#!/usr/bin/env python3
"""v286 Android/TWRP/native ICNSS boot timing comparator.

The comparator is read-only.  It consumes existing Android/TWRP evidence and
optionally collects current native-init evidence through cmdv1.  It does not
start Wi-Fi daemons, does not send QMI/QRTR packets, and does not mutate sysfs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v286-icnss-boot-timing")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v204-android-baseline/root-dmesg-wifi-tail.txt")
DEFAULT_ANDROID_MANIFEST = Path("tmp/wifi/v204-android-baseline/manifest.json")
DEFAULT_TWRP_MANIFEST = Path("tmp/wifi/v204-twrp-baseline/manifest.json")
DEFAULT_TOYBOX = "/cache/bin/toybox"

TIMESTAMP_RE = re.compile(r"^\[\s*(?P<seconds>\d+(?:\.\d+)?)\]\s*(?P<message>.*)$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
FOCUS_RE = re.compile(r"(icnss|cnss|wlfw|qmi|qca6390|wlan|wifi|wiphy|rfkill|firmware|fw|bdf|wificond|supplicant)", re.IGNORECASE)
WRAPPER_RE = re.compile(r"^(?:a90:/#|A90P1 BEGIN |A90P1 END |\[done\]|\[exit |run: pid=)")
WLAN_NETDEV_RE = re.compile(r"(^|\s)(wlan\d+|swlan\d+|p2p\d+)(:|\s+Link encap|\s+->|\s+<)", re.IGNORECASE)
WIPHY_RFKILL_RE = re.compile(r"(ieee80211|phy\d+|wiphy|rfkill\d+.*icnss|icnss/.*/rfkill)", re.IGNORECASE)


@dataclass
class Event:
    source: str
    kind: str
    seconds: float | None
    line: str


@dataclass
class SourceSummary:
    name: str
    present: bool
    text_file: str | None
    line_count: int
    focus_line_count: int
    events: list[Event]


EVENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("icnss_platform_probe", re.compile(r"icnss: Platform driver probed successfully|sec_create_wifi_sysfs done|Recursive recovery allowed for WLAN", re.I)),
    ("android_wifi_action", re.compile(r"processing action .*wifi\.rc|Wifi Turning On|wifi_hal_ext", re.I)),
    ("wifi_hal_start", re.compile(r"starting service 'vendor\.wifi_hal|android\.hardware\.wifi", re.I)),
    ("cnss_diag_start", re.compile(r"starting service 'cnss_diag'|comm:\s*cnss_diag|comm:cnss_diag", re.I)),
    ("wificond_start", re.compile(r"starting service 'wificond'|comm:\s*wificond|comm:wificond", re.I)),
    ("cnss_daemon_start", re.compile(r"starting service 'cnss-daemon'|comm:\s*cnss-daemon|comm:cnss-daemon", re.I)),
    ("wlfw_start", re.compile(r"wlfw_start|wlfw_service_request", re.I)),
    ("qmi_server_connected", re.compile(r"QMI Server Connected|qmi.*connected|service-notifier.*wlan_pd", re.I)),
    ("bdf_download", re.compile(r"BDF file|bdwlan|regdb", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready|FW ready event received|wma_wait_for_ready_event", re.I)),
    ("firmware_load", re.compile(r"firmware: loading|WCNSS_qcom_cfg|wlanmdsp", re.I)),
    ("wlan_driver_log", re.compile(r"\bwlan:\s*\[|HostSW:|Firmware build version|Target Ready", re.I)),
    ("fw_ready_event", re.compile(r"ready_extract_init_status|wma_rx_service_ready_event|FW ready event", re.I)),
    ("wlan_netdev", WLAN_NETDEV_RE),
    ("wiphy_rfkill", WIPHY_RFKILL_RE),
)

EXPECTED_ANDROID_CHAIN = (
    "icnss_platform_probe",
    "android_wifi_action",
    "wifi_hal_start",
    "cnss_diag_start",
    "wificond_start",
    "cnss_daemon_start",
    "wlfw_start",
    "qmi_server_connected",
    "bdf_download",
    "wlan_fw_ready",
    "firmware_load",
    "wlan_driver_log",
    "fw_ready_event",
    "wlan_netdev",
    "wiphy_rfkill",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = ANSI_RE.sub("", raw).strip().replace("<NULL>", "")
        if not line or WRAPPER_RE.match(line):
            continue
        if line in {"OK", "OK authenticated", "pong"}:
            continue
        if re.fullmatch(r"\[(?:pid|exit)\s+-?\d+\]", line):
            continue
        lines.append(line)
    return lines


def focus_lines(text: str) -> list[str]:
    return [line for line in clean_lines(text) if FOCUS_RE.search(line)]


def parse_seconds(line: str) -> tuple[float | None, str]:
    match = TIMESTAMP_RE.match(line)
    if not match:
        return None, line
    return float(match.group("seconds")), match.group("message")


def extract_events(source: str, text: str) -> list[Event]:
    events: list[Event] = []
    seen: set[tuple[str, str]] = set()
    for line in clean_lines(text):
        seconds, message = parse_seconds(line)
        target = message if seconds is not None else line
        for kind, pattern in EVENT_PATTERNS:
            if not pattern.search(target):
                continue
            key = (kind, line)
            if key in seen:
                continue
            seen.add(key)
            events.append(Event(source, kind, seconds, line))
    events.sort(key=lambda item: (float("inf") if item.seconds is None else item.seconds, item.kind, item.line))
    return events


def read_text_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def manifest_texts(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return []
    texts: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "text" and isinstance(item, str):
                    texts.append(item)
                elif key.endswith("_evidence") and isinstance(item, list):
                    texts.extend(str(line) for line in item)
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    return texts


def source_summary(name: str, text: str, text_file: str | None = None) -> SourceSummary:
    focused = focus_lines(text)
    return SourceSummary(
        name=name,
        present=bool(text.strip()),
        text_file=text_file,
        line_count=len(clean_lines(text)),
        focus_line_count=len(focused),
        events=extract_events(name, text),
    )


def collect_native(args: argparse.Namespace, store: EvidenceStore) -> tuple[str, list[dict[str, Any]]]:
    commands: tuple[tuple[str, list[str], float], ...] = (
        ("version", ["version"], 10.0),
        ("dmesg", ["run", args.toybox, "dmesg"], 45.0),
        ("proc-net-dev", ["run", args.toybox, "cat", "/proc/net/dev"], 10.0),
        ("sys-class-net", ["run", args.toybox, "ls", "-l", "/sys/class/net"], 10.0),
        ("sys-class-ieee80211", ["run", args.toybox, "ls", "-l", "/sys/class/ieee80211"], 10.0),
        ("sys-class-rfkill", ["run", args.toybox, "ls", "-l", "/sys/class/rfkill"], 10.0),
        ("proc-modules", ["run", args.toybox, "cat", "/proc/modules"], 20.0),
        ("ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm"], 20.0),
    )
    captures: list[dict[str, Any]] = []
    text_parts: list[str] = []
    store.mkdir("native")
    for name, command, timeout in commands:
        capture = run_capture(args, name, command, timeout=timeout)
        text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
        relative = f"native/{safe_name(name)}.txt"
        store.write_text(relative, text)
        item = asdict(capture)
        item["file"] = relative
        item["text"] = text[:4096] + ("\n[truncated in manifest]\n" if len(text) > 4096 else "")
        captures.append(item)
        if name != "version":
            text_parts.append(text)
    return "\n".join(text_parts), captures


def kind_index(summary: SourceSummary, max_seconds: float | None = None) -> dict[str, Event]:
    result: dict[str, Event] = {}
    for event in summary.events:
        if max_seconds is not None and event.seconds is not None and event.seconds > max_seconds:
            continue
        result.setdefault(event.kind, event)
    return result


def compare_sources(android: SourceSummary,
                    twrp: SourceSummary,
                    native: SourceSummary,
                    *,
                    native_boot_window_sec: float) -> dict[str, Any]:
    android_index = kind_index(android)
    twrp_index = kind_index(twrp)
    native_index = kind_index(native, max_seconds=native_boot_window_sec)
    native_late_events = [
        event for event in native.events
        if event.seconds is not None and event.seconds > native_boot_window_sec
    ]
    rows: list[dict[str, Any]] = []
    missing_native: list[str] = []
    for kind in EXPECTED_ANDROID_CHAIN:
        android_event = android_index.get(kind)
        twrp_event = twrp_index.get(kind)
        native_event = native_index.get(kind)
        rows.append(
            {
                "kind": kind,
                "android": android_event.seconds if android_event else None,
                "twrp": twrp_event.seconds if twrp_event else None,
                "native": native_event.seconds if native_event else None,
                "android_line": android_event.line if android_event else "",
                "twrp_line": twrp_event.line if twrp_event else "",
                "native_line": native_event.line if native_event else "",
            }
        )
        if android_event is not None and native_event is None:
            missing_native.append(kind)
    first_missing = missing_native[0] if missing_native else None
    return {
        "rows": rows,
        "missing_native": missing_native,
        "first_missing_native": first_missing,
        "android_event_count": len(android.events),
        "twrp_event_count": len(twrp.events),
        "native_event_count": len(native.events),
        "native_boot_window_sec": native_boot_window_sec,
        "native_late_event_count": len(native_late_events),
    }


def classify(manifest: dict[str, Any]) -> tuple[bool, str, str]:
    if manifest["mode"] == "plan":
        return True, "icnss-boot-timing-plan-ready", "timing comparator plan is ready; no device command executed"
    if not manifest.get("native_version_matches"):
        return False, "icnss-boot-timing-version-mismatch", "native init version did not match expected build"
    sources = manifest["sources"]
    if not sources["android"]["present"]:
        return False, "icnss-boot-timing-input-missing", "Android dmesg/baseline input is missing"
    if not sources["native"]["present"]:
        return False, "icnss-boot-timing-native-capture-failed", "native evidence is missing"
    comparison = manifest["comparison"]
    if comparison["android_event_count"] == 0:
        return True, "icnss-boot-timing-refresh-needed", "Android input exists but has no parseable ICNSS/WLAN timing events"
    if comparison["native_event_count"] == 0:
        return True, "icnss-boot-timing-gap-mapped", "native has no parseable ICNSS/WLAN timing events beyond static evidence"
    if comparison["missing_native"]:
        first = comparison["first_missing_native"]
        return True, "icnss-boot-timing-gap-mapped", f"first Android timing event missing in native: {first}"
    return True, "icnss-boot-timing-no-gap", "native evidence contains all Android timing event classes"


def render_summary(manifest: dict[str, Any]) -> str:
    source_rows = [
        [
            name,
            "yes" if data["present"] else "no",
            str(data["line_count"]),
            str(data["focus_line_count"]),
            str(data["event_count"]),
        ]
        for name, data in manifest["sources"].items()
    ]
    timing_rows = []
    for row in manifest["comparison"]["rows"]:
        timing_rows.append([
            row["kind"],
            "" if row["android"] is None else f"{row['android']:.3f}",
            "" if row["twrp"] is None else f"{row['twrp']:.3f}",
            "" if row["native"] is None else f"{row['native']:.3f}",
        ])
    missing = manifest["comparison"]["missing_native"]
    lines = [
        "# ICNSS Boot Timing Compare\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- mode: `{manifest['mode']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: {manifest['reason']}\n\n",
        "## Sources\n\n",
        markdown_table(["source", "present", "lines", "focus lines", "events"], source_rows),
        "\n\n## Timing Matrix\n\n",
        markdown_table(["event", "android_s", "twrp_s", "native_s"], timing_rows),
        "\n\n## Missing Native Events\n\n",
    ]
    if missing:
        lines.extend(f"- `{item}`\n" for item in missing)
    else:
        lines.append("- none\n")
    lines.extend([
        "\n## Guardrails\n\n",
        "- no daemon execution\n",
        "- no QMI payload\n",
        "- no QRTR nameservice packet\n",
        "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing\n",
        "- no rfkill write\n",
        "- no ICNSS bind/unbind\n",
        "- no reboot/recovery/poweroff\n",
    ])
    return "".join(lines)


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    native_captures: list[dict[str, Any]] = []

    android_file = repo_path(args.android_dmesg)
    android_parts = []
    android_file_text = read_text_file(android_file)
    if android_file_text:
        android_parts.append(android_file_text)
    android_parts.extend(manifest_texts(repo_path(args.android_manifest)))
    android_text = "\n".join(android_parts)
    twrp_text = "\n".join(manifest_texts(repo_path(args.twrp_manifest)))

    native_text = ""
    if args.command == "run" and not args.no_collect_native:
        native_text, native_captures = collect_native(args, store)
    elif args.native_file:
        native_text = read_text_file(repo_path(args.native_file))

    android_summary = source_summary("android", android_text, str(android_file) if android_file.exists() else str(args.android_manifest))
    twrp_summary = source_summary("twrp", twrp_text, str(args.twrp_manifest))
    native_summary = source_summary("native", native_text, str(args.native_file) if args.native_file else "live-cmdv1")
    comparison = compare_sources(
        android_summary,
        twrp_summary,
        native_summary,
        native_boot_window_sec=args.native_boot_window_sec,
    )

    def source_payload(summary: SourceSummary) -> dict[str, Any]:
        return {
            "present": summary.present,
            "text_file": summary.text_file,
            "line_count": summary.line_count,
            "focus_line_count": summary.focus_line_count,
            "event_count": len(summary.events),
            "events": [asdict(event) for event in summary.events[:80]],
        }

    native_version_text = ""
    for capture in native_captures:
        if capture.get("name") == "version":
            native_version_text = str(capture.get("text", ""))
            break
    native_version_matches = args.command == "plan" or args.expect_version in native_version_text or bool(args.native_file)
    manifest: dict[str, Any] = {
        "created": now_iso(),
        "mode": args.command,
        "host_metadata": collect_host_metadata(),
        "out_dir": str(out_dir),
        "expect_version": args.expect_version,
        "native_version_matches": native_version_matches,
        "sources": {
            "android": source_payload(android_summary),
            "twrp": source_payload(twrp_summary),
            "native": source_payload(native_summary),
        },
        "native_captures": native_captures,
        "comparison": comparison,
        "guardrails": [
            "no daemon execution",
            "no QMI payload",
            "no QRTR nameservice packet",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill write",
            "no ICNSS bind/unbind",
            "no reboot/recovery/poweroff",
        ],
    }
    pass_ok, decision, reason = classify(manifest)
    manifest["pass"] = pass_ok
    manifest["decision"] = decision
    manifest["reason"] = reason
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--android-manifest", type=Path, default=DEFAULT_ANDROID_MANIFEST)
    parser.add_argument("--twrp-manifest", type=Path, default=DEFAULT_TWRP_MANIFEST)
    parser.add_argument("--native-file", type=Path)
    parser.add_argument("--no-collect-native", action="store_true")
    parser.add_argument("--native-boot-window-sec", type=float, default=300.0)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    args = parser.parse_args()
    if args.command == "plan":
        args.no_collect_native = True
    return args


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {manifest['out_dir']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
