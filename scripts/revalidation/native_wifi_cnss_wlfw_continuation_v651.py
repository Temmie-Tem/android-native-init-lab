#!/usr/bin/env python3
"""V651 host-only CNSS/WLFW continuation classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v651-cnss-wlfw-continuation")
DEFAULT_V650_MANIFEST = Path("tmp/wifi/v650-post-warning-continuation/manifest.json")
DEFAULT_ANDROID_DMESG = Path(
    "tmp/wifi/v649-android-full-audio-wifi-handoff-live-20260523-074556/"
    "v649-android-full-audio-wifi-recapture-run/android/commands/dmesg-audio-wifi-tail.txt"
)
DEFAULT_NATIVE_DMESG = Path("tmp/wifi/v644-live-20260523-071610/native/dmesg-delta.txt")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("qos_warning", re.compile(r"WARNING: CPU:.*kernel/power/qos\.c:616", re.I)),
    ("sound_card_registered", re.compile(r"Sound card .* registered", re.I)),
    ("cnss_diag_start", re.compile(r"starting service 'cnss_diag'", re.I)),
    ("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag", re.I)),
    ("cnss_diag_cld80211", re.compile(r"cnss_diag.*ctrl_getfamily.*cld80211", re.I)),
    ("cnss_daemon_start", re.compile(r"starting service 'cnss-daemon'", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_cld80211", re.compile(r"cnss-daemon.*ctrl_getfamily.*cld80211", re.I)),
    ("cnss_genl_fail_continue", re.compile(r"cnss-daemon Failed to init genl.*continue", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting|\bwlfw_start\b", re.I)),
    ("wlfw_service_request", re.compile(r"cnss-daemon wlfw_service_request", re.I)),
    ("wlan_mac_fail", re.compile(r"cnss-daemon .*WLAN MAC|cnss-daemon .*DMS get mac", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*wlan_pd|wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin|regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin|bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("binder_ioctl_error", re.compile(r"cnss-daemon.*binder:.*ioctl .* returned -22", re.I)),
    ("binder_transaction_failed", re.compile(r"cnss-daemon.*binder:.*transaction failed .*?-22", re.I)),
)

TIMELINE = (
    "service_notifier_74",
    "qos_warning",
    "sound_card_registered",
    "cnss_diag_start",
    "cnss_diag_netlink",
    "cnss_diag_cld80211",
    "cnss_daemon_start",
    "cnss_daemon_netlink",
    "cnss_daemon_cld80211",
    "cnss_genl_fail_continue",
    "wlfw_start",
    "wlfw_service_request",
    "wlan_mac_fail",
    "wlan_pd",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0",
    "binder_ioctl_error",
    "binder_transaction_failed",
)

FORBIDDEN_ACTIONS = (
    "device command",
    "sysfs write",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
)


@dataclass(frozen=True)
class Event:
    marker: str
    timestamp: float | None
    line: str
    source: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v650-manifest", type=Path, default=DEFAULT_V650_MANIFEST)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--native-dmesg", type=Path, default=DEFAULT_NATIVE_DMESG)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def clean_line(raw_line: str) -> str:
    return ANSI_RE.sub("", raw_line).strip()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def line_time(line: str) -> float | None:
    match = TS_RE.match(clean_line(line))
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_events(text: str, source: str) -> list[Event]:
    events: list[Event] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if not line or line.startswith("$ ") or line.startswith("rc="):
            continue
        for marker, pattern in PATTERNS:
            if pattern.search(line):
                events.append(Event(marker, line_time(line), line, source))
    return events


def first_by_marker(events: list[Event]) -> dict[str, Event]:
    first: dict[str, Event] = {}
    for event in events:
        first.setdefault(event.marker, event)
    return first


def count_by_marker(events: list[Event]) -> dict[str, int]:
    counts = {marker: 0 for marker in TIMELINE}
    for event in events:
        counts[event.marker] = counts.get(event.marker, 0) + 1
    return counts


def event_time(first: dict[str, Event], marker: str) -> float | None:
    event = first.get(marker)
    return event.timestamp if event else None


def delta_ms(first: dict[str, Event], later: str, earlier: str) -> float | None:
    later_time = event_time(first, later)
    earlier_time = event_time(first, earlier)
    if later_time is None or earlier_time is None:
        return None
    return round((later_time - earlier_time) * 1000.0, 3)


def timeline_rows(first: dict[str, Event], counts: dict[str, int]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in TIMELINE:
        event = first.get(marker)
        rows.append([
            marker,
            str(counts.get(marker, 0)),
            "" if event is None or event.timestamp is None else f"{event.timestamp:.6f}",
            "missing" if event is None else event.line,
        ])
    return rows


def timeline_map(rows: list[list[str]]) -> dict[str, dict[str, str]]:
    return {
        row[0]: {
            "count": row[1],
            "first_timestamp": row[2],
            "first_line": row[3],
        }
        for row in rows
    }


def rows_to_dicts(headers: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
    return [dict(zip(headers, row, strict=True)) for row in rows]


def source_summary(events: list[Event]) -> dict[str, Any]:
    first = first_by_marker(events)
    counts = count_by_marker(events)
    rows = timeline_rows(first, counts)
    return {
        "counts": counts,
        "first_times": {marker: event_time(first, marker) for marker in TIMELINE},
        "first_lines": {
            marker: first.get(marker, Event(marker, None, "missing", "")).line for marker in TIMELINE
        },
        "timeline_rows": rows,
        "timeline": timeline_map(rows),
        "deltas_ms": {
            "service74_to_qos_warning": delta_ms(first, "qos_warning", "service_notifier_74"),
            "service74_to_cnss_diag_netlink": delta_ms(first, "cnss_diag_netlink", "service_notifier_74"),
            "service74_to_cnss_daemon_netlink": delta_ms(first, "cnss_daemon_netlink", "service_notifier_74"),
            "cnss_daemon_netlink_to_genl_fail": delta_ms(first, "cnss_genl_fail_continue", "cnss_daemon_netlink"),
            "cnss_daemon_netlink_to_wlfw_start": delta_ms(first, "wlfw_start", "cnss_daemon_netlink"),
            "genl_fail_to_wlfw_start": delta_ms(first, "wlfw_start", "cnss_genl_fail_continue"),
            "wlfw_start_to_wlan_pd": delta_ms(first, "wlan_pd", "wlfw_start"),
            "wlfw_start_to_qmi_server_connected": delta_ms(first, "qmi_server_connected", "wlfw_start"),
            "wlfw_start_to_bdf_regdb": delta_ms(first, "bdf_regdb", "wlfw_start"),
            "cnss_daemon_netlink_to_binder_ioctl": delta_ms(first, "binder_ioctl_error", "cnss_daemon_netlink"),
            "cnss_daemon_netlink_to_binder_transaction": delta_ms(first, "binder_transaction_failed", "cnss_daemon_netlink"),
            "binder_ioctl_to_binder_transaction": delta_ms(first, "binder_transaction_failed", "binder_ioctl_error"),
        },
    }


def matrix_rows(android: dict[str, Any], native: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for marker in TIMELINE:
        rows.append([
            marker,
            str(android["counts"].get(marker, 0)),
            str(android["first_times"].get(marker)),
            str(native["counts"].get(marker, 0)),
            str(native["first_times"].get(marker)),
        ])
    return rows


def inference_rows(manifest: dict[str, Any]) -> list[list[str]]:
    checks = manifest["checks"]
    android = manifest["android"]
    native = manifest["native_v644"]
    return [
        [
            "Android CNSS path",
            "continues",
            (
                f"netlink={android['counts'].get('cnss_daemon_netlink', 0)}; "
                f"genl_fail={android['counts'].get('cnss_genl_fail_continue', 0)}; "
                f"wlfw={android['counts'].get('wlfw_start', 0)}; "
                f"wlan_pd={android['counts'].get('wlan_pd', 0)}"
            ),
            "Android genl failure is non-fatal because WLFW follows it",
        ],
        [
            "Native CNSS path",
            "stalls before WLFW",
            (
                f"netlink={native['counts'].get('cnss_daemon_netlink', 0)}; "
                f"cld80211={native['counts'].get('cnss_daemon_cld80211', 0)}; "
                f"wlfw={native['counts'].get('wlfw_start', 0)}"
            ),
            "native reaches CNSS netlink/cld80211 but does not enter WLFW",
        ],
        [
            "Native binder path",
            "active blocker candidate",
            (
                f"ioctl_error={native['counts'].get('binder_ioctl_error', 0)}; "
                f"transaction_failed={native['counts'].get('binder_transaction_failed', 0)}; "
                f"netlink_to_ioctl={native['deltas_ms'].get('cnss_daemon_netlink_to_binder_ioctl')}ms"
            ),
            "service-manager/binder runtime parity is the next bounded proof target",
        ],
        [
            "WLFW/BDF/wlan0",
            "still blocked in native",
            (
                f"android_wlfw_qmi_bdf={checks['android_reaches_wlfw_qmi_bdf']}; "
                f"native_missing_wlfw_qmi_bdf={checks['native_missing_wlfw_qmi_bdf']}"
            ),
            "do not start Wi-Fi HAL or scan/connect until native reaches WLFW/BDF",
        ],
    ]


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    checks = manifest["checks"]
    if (
        checks["v650_passed"]
        and checks["android_cnss_daemon_reaches_wlfw"]
        and checks["android_genl_failure_is_nonfatal"]
        and checks["native_cnss_daemon_reaches_netlink"]
        and checks["native_binder_errors_present"]
        and checks["native_wlfw_absent"]
    ):
        return (
            "v651-cnss-daemon-binder-blocks-wlfw-continuation",
            True,
            (
                "Android and native both reach CNSS netlink class evidence, but Android treats "
                "the genl failure as non-fatal and enters WLFW while native repeats cnss-daemon "
                "binder -22 failures and never reaches WLFW/WLAN-PD/QMI/BDF/wlan0."
            ),
            "plan V652 bounded service-manager/binder-runtime parity proof around cnss-daemon; keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping blocked",
        )

    return (
        "v651-cnss-wlfw-review-required",
        False,
        "CNSS/WLFW continuation evidence did not match the expected Android-vs-native binder gap",
        "inspect V649/V644 dmesg manually before live retry",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v650 = load_json(args.v650_manifest)
    android = source_summary(parse_events(read_text(args.android_dmesg), "android-v649"))
    native = source_summary(parse_events(read_text(args.native_dmesg), "native-v644"))
    checks = {
        "v650_passed": bool(v650.get("pass")),
        "android_cnss_daemon_reaches_wlfw": (
            android["counts"].get("cnss_daemon_netlink", 0) > 0
            and android["counts"].get("wlfw_start", 0) > 0
            and android["counts"].get("wlfw_service_request", 0) > 0
        ),
        "android_genl_failure_is_nonfatal": (
            android["counts"].get("cnss_genl_fail_continue", 0) > 0
            and android["deltas_ms"].get("genl_fail_to_wlfw_start") is not None
            and android["deltas_ms"]["genl_fail_to_wlfw_start"] > 0
        ),
        "android_reaches_wlfw_qmi_bdf": all(
            android["counts"].get(marker, 0) > 0
            for marker in ("wlfw_start", "wlan_pd", "qmi_server_connected", "bdf_regdb", "bdf_bdwlan")
        ),
        "android_binder_errors_absent": (
            android["counts"].get("binder_ioctl_error", 0) == 0
            and android["counts"].get("binder_transaction_failed", 0) == 0
        ),
        "native_cnss_daemon_reaches_netlink": (
            native["counts"].get("cnss_daemon_netlink", 0) > 0
            and native["counts"].get("cnss_daemon_cld80211", 0) > 0
        ),
        "native_binder_errors_present": (
            native["counts"].get("binder_ioctl_error", 0) > 0
            and native["counts"].get("binder_transaction_failed", 0) > 0
        ),
        "native_wlfw_absent": native["counts"].get("wlfw_start", 0) == 0,
        "native_missing_wlfw_qmi_bdf": all(
            native["counts"].get(marker, 0) == 0
            for marker in ("wlfw_start", "wlan_pd", "qmi_server_connected", "bdf_regdb", "bdf_bdwlan", "wlan0")
        ),
    }
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "v650_manifest": str(repo_path(args.v650_manifest)),
            "android_dmesg": str(repo_path(args.android_dmesg)),
            "native_dmesg": str(repo_path(args.native_dmesg)),
        },
        "prior": {
            "v650": {
                "decision": v650.get("decision"),
                "pass": v650.get("pass"),
            }
        },
        "android": android,
        "native_v644": native,
        "checks": checks,
        "matrix_rows": matrix_rows(android, native),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "sysfs_writes_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }

    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v651-cnss-wlfw-continuation-plan-ready",
            True,
            "plan-only; no device contact, no daemon start, no Wi-Fi bring-up",
            "run V651 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(manifest)

    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
    })
    manifest["matrix"] = rows_to_dicts(
        ["marker", "android_count", "android_first_time", "native_count", "native_first_time"],
        manifest["matrix_rows"],
    )
    manifest["inference_rows"] = inference_rows(manifest)
    manifest["inferences"] = rows_to_dicts(
        ["subject", "classification", "evidence", "next"],
        manifest["inference_rows"],
    )
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V651 CNSS/WLFW Continuation Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "value"], [[key, str(value)] for key, value in manifest["checks"].items()]),
        "",
        "## Key Deltas",
        "",
        markdown_table(
            ["source", "delta", "ms"],
            [["android", key, str(value)] for key, value in manifest["android"]["deltas_ms"].items()]
            + [["native_v644", key, str(value)] for key, value in manifest["native_v644"]["deltas_ms"].items()],
        ),
        "",
        "## Inferences",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["inference_rows"]),
        "",
        "## Marker Matrix",
        "",
        markdown_table(
            ["marker", "android_count", "android_first_time", "native_count", "native_first_time"],
            manifest["matrix_rows"],
        ),
        "",
        "## Interpretation",
        "",
        "- V650 already proved the ASoC warning itself is not the final stop condition.",
        "- V651 moves the blocker to the CNSS daemon continuation boundary.",
        "- Android reaches WLFW after a non-fatal genl failure.",
        "- Native reaches CNSS netlink/cld80211, then repeats binder `-22` failures and never reaches WLFW.",
        "- The next live gate should be a bounded service-manager/binder-runtime parity proof, not Wi-Fi HAL or scan/connect.",
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
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
