#!/usr/bin/env python3
"""V696 host-only post-provider CNSS retry blocker classifier.

This classifier consumes the V695 provider-confirmed CNSS retry proof and an
Android reference dmesg tail. It does not contact the device, start daemons,
mount filesystems, scan/connect, use credentials, run DHCP, change routes, or
ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v696-post-provider-retry-blocker-classifier")
DEFAULT_V695_MANIFEST = Path("tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/manifest.json")
DEFAULT_V695_DMESG = Path(
    "tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/"
    "arm-v695-v118-provider-confirmed-cnss-retry/live/native/dmesg-delta.txt"
)
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v515-android-native-sequence-delta/inputs/android-dmesg-wifi-cnss-tail.txt")

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

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
TS_RE = re.compile(r"\[\s*(?P<ts>\d+\.\d+)\]")

MARKERS: dict[str, re.Pattern[str]] = {
    "qrtr_rx": re.compile(r"qrtr: Modem QMI Readiness RX", re.I),
    "qrtr_tx": re.compile(r"qrtr: Modem QMI Readiness TX", re.I),
    "sysmon_modem": re.compile(r"sysmon-qmi: .*modem's SSCTL service", re.I),
    "sysmon_esoc0": re.compile(r"sysmon-qmi: .*esoc0's SSCTL service", re.I),
    "service_180": re.compile(r"service-notifier: .* 180 service", re.I),
    "service_74": re.compile(r"service-notifier: .* 74 service", re.I),
    "service_ind_wlan_pd": re.compile(r"service-notifier: root_service_service_ind_cb: .*wlan_pd", re.I),
    "cnss_diag_start": re.compile(r"starting service 'cnss_diag'|cnss_diag:.*netlink_create|netlink_create.*comm: cnss_diag", re.I),
    "cnss_daemon_start": re.compile(r"starting service 'cnss-daemon'|cnss-daemon:.*netlink_create|netlink_create.*comm: cnss-daemon", re.I),
    "cnss_daemon_netlink": re.compile(r"cnss-daemon.*netlink_create|netlink_create.*comm: cnss-daemon", re.I),
    "cnss_binder_fail": re.compile(r"cnss-daemon.*binder:.*transaction failed .*?-22", re.I),
    "binder_ioctl_fail": re.compile(r"binder: .* ioctl .* returned -22", re.I),
    "pm_qos_duplicate": re.compile(r"pm_qos_add_request\(\) called for already added request", re.I),
    "pm_qos_warning": re.compile(r"WARNING: CPU: .*pm_qos_add_request", re.I),
    "wlfw_start": re.compile(r"cnss-daemon wlfw_start: Starting", re.I),
    "wlfw_service_request": re.compile(r"cnss-daemon wlfw_service_request", re.I),
    "wlan_pd": re.compile(r"\bwlan_pd\b", re.I),
    "qmi_server_connected": re.compile(r"icnss_qmi: QMI Server Connected", re.I),
    "bdf_regdb": re.compile(r"BDF file\s*:\s*regdb\.bin", re.I),
    "bdf_bdwlan": re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I),
    "wlan_fw_ready": re.compile(r"icnss: WLAN FW is ready", re.I),
    "wlan_driver_load": re.compile(r"wlan: Loading driver", re.I),
    "wlan0": re.compile(r"\bwlan0\b", re.I),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v695-manifest", type=Path, default=DEFAULT_V695_MANIFEST)
    parser.add_argument("--v695-dmesg", type=Path, default=DEFAULT_V695_DMESG)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
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


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ready"}


def intish(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def strip_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def line_ts(line: str) -> float | None:
    match = TS_RE.search(line)
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_timeline(text: str) -> dict[str, Any]:
    events: dict[str, list[dict[str, Any]]] = {name: [] for name in MARKERS}
    for raw in text.splitlines():
        line = strip_line(raw)
        if not line:
            continue
        timestamp = line_ts(line)
        for name, pattern in MARKERS.items():
            if pattern.search(line):
                events[name].append({"ts": timestamp, "line": line[:260]})
    return {
        "counts": {name: len(rows) for name, rows in events.items()},
        "first_ts": {name: rows[0]["ts"] for name, rows in events.items() if rows and rows[0]["ts"] is not None},
        "first_lines": {name: rows[0]["line"] for name, rows in events.items() if rows},
        "sample_lines": {name: [row["line"] for row in rows[:4]] for name, rows in events.items() if rows},
    }


def delta(first_ts: dict[str, float], start: str, end: str) -> float | None:
    if start not in first_ts or end not in first_ts:
        return None
    return round((first_ts[end] - first_ts[start]) * 1000.0, 3)


def deltas_for(timeline: dict[str, Any]) -> dict[str, float | None]:
    first_ts = timeline.get("first_ts") or {}
    return {
        "service74_to_pm_qos_duplicate_ms": delta(first_ts, "service_74", "pm_qos_duplicate"),
        "service74_to_cnss_daemon_netlink_ms": delta(first_ts, "service_74", "cnss_daemon_netlink"),
        "service74_to_cnss_binder_fail_ms": delta(first_ts, "service_74", "cnss_binder_fail"),
        "service74_to_wlfw_start_ms": delta(first_ts, "service_74", "wlfw_start"),
        "cnss_daemon_netlink_to_binder_fail_ms": delta(first_ts, "cnss_daemon_netlink", "cnss_binder_fail"),
        "cnss_daemon_netlink_to_wlfw_start_ms": delta(first_ts, "cnss_daemon_netlink", "wlfw_start"),
        "wlfw_start_to_wlan_pd_ms": delta(first_ts, "wlfw_start", "service_ind_wlan_pd"),
        "wlfw_start_to_qmi_server_ms": delta(first_ts, "wlfw_start", "qmi_server_connected"),
        "wlfw_start_to_bdf_regdb_ms": delta(first_ts, "wlfw_start", "bdf_regdb"),
        "wlfw_start_to_fw_ready_ms": delta(first_ts, "wlfw_start", "wlan_fw_ready"),
    }


def arm_v695(manifest: dict[str, Any]) -> dict[str, Any]:
    arm = manifest.get("arm_v695")
    return arm if isinstance(arm, dict) else {}


def build_surface(v695_manifest: dict[str, Any], v695_text: str, android_text: str) -> dict[str, Any]:
    native_timeline = parse_timeline(v695_text)
    android_timeline = parse_timeline(android_text)
    arm = arm_v695(v695_manifest)
    counts = arm.get("counts") or {}
    peripheral = arm.get("peripheral") or {}
    retry = peripheral.get("cnss_retry") if isinstance(peripheral.get("cnss_retry"), dict) else {}
    return {
        "v695": {
            "decision": v695_manifest.get("decision", ""),
            "pass": boolish(v695_manifest.get("pass")),
            "query_exact_match": boolish(arm.get("query_exact_match")),
            "cnss_retry_started": boolish(arm.get("cnss_retry_started")) or bool(retry.get("retry_start_order")),
            "cnss_retry": retry,
            "counts": counts,
            "service74": intish(counts.get("service_notifier_74")),
            "cnss_netlink": intish(counts.get("cnss_daemon_netlink")),
            "cnss_cld80211": intish(counts.get("cnss_daemon_cld80211")),
            "cnss_binder_tx": intish(counts.get("cnss_binder_transaction_failed")),
            "kernel_warning": intish(counts.get("kernel_warning")),
            "qmi_server_connected": intish(counts.get("qmi_server_connected")),
            "wlfw_start": intish(counts.get("wlfw_start")),
            "bdf_bdwlan": intish(counts.get("bdf_bdwlan")),
            "wlan_fw_ready": intish(counts.get("wlan_fw_ready")),
            "wlan0": intish(counts.get("wlan0")),
        },
        "native_timeline": native_timeline,
        "native_deltas_ms": deltas_for(native_timeline),
        "android_timeline": android_timeline,
        "android_deltas_ms": deltas_for(android_timeline),
    }


def count(surface: dict[str, Any], side: str, marker: str) -> int:
    return intish(((surface.get(side) or {}).get("counts") or {}).get(marker))


def build_checks(surface: dict[str, Any]) -> list[dict[str, Any]]:
    v695 = surface["v695"]
    native = surface["native_timeline"]
    android = surface["android_timeline"]
    android_deltas = surface["android_deltas_ms"]
    native_deltas = surface["native_deltas_ms"]
    return [
        {
            "name": "input-evidence-ready",
            "status": "pass" if v695["pass"] and count(surface, "native_timeline", "service_74") > 0 and count(surface, "android_timeline", "service_74") > 0 else "blocked",
            "detail": {
                "v695_decision": v695["decision"],
                "native_dmesg_has_service74": count(surface, "native_timeline", "service_74"),
                "android_dmesg_has_service74": count(surface, "android_timeline", "service_74"),
            },
            "next_step": "refresh V695 or Android reference evidence",
        },
        {
            "name": "provider-confirmed-cnss-retry-executed",
            "status": "pass" if v695["query_exact_match"] and v695["cnss_retry_started"] else "blocked",
            "detail": {
                "query_exact_match": v695["query_exact_match"],
                "cnss_retry_started": v695["cnss_retry_started"],
                "cnss_retry": v695["cnss_retry"],
            },
            "next_step": "do not classify post-provider blocker until V695 retry gate is true",
        },
        {
            "name": "android-reference-reaches-wlfw-bdf-fwready",
            "status": "finding" if (
                count(surface, "android_timeline", "wlfw_start") > 0
                and count(surface, "android_timeline", "bdf_bdwlan") > 0
                and count(surface, "android_timeline", "wlan_fw_ready") > 0
            ) else "review",
            "detail": {
                "counts": android["counts"],
                "deltas_ms": android_deltas,
            },
            "next_step": "recapture Android dmesg if the reference no longer includes WLFW/BDF/FW-ready",
        },
        {
            "name": "native-stalls-after-cnss-retry-before-wlfw",
            "status": "finding" if (
                v695["service74"] > 0
                and v695["cnss_netlink"] > 0
                and v695["cnss_retry_started"]
                and v695["wlfw_start"] == 0
                and v695["bdf_bdwlan"] == 0
                and v695["wlan0"] == 0
            ) else "review",
            "detail": {
                "v695_counts": v695["counts"],
                "native_deltas_ms": native_deltas,
            },
            "next_step": "keep scan/connect blocked until WLFW/BDF/wlan0 appears",
        },
        {
            "name": "cnss-binder-failure-remains-native-only",
            "status": "finding" if (
                v695["cnss_binder_tx"] > 0
                and count(surface, "native_timeline", "cnss_binder_fail") > 0
                and count(surface, "android_timeline", "cnss_binder_fail") == 0
            ) else "review",
            "detail": {
                "native_count": count(surface, "native_timeline", "cnss_binder_fail"),
                "android_count": count(surface, "android_timeline", "cnss_binder_fail"),
                "native_line": native["first_lines"].get("cnss_binder_fail", ""),
                "native_deltas_ms": native_deltas,
            },
            "next_step": "classify or repair native cnss-daemon Binder runtime after provider registration",
        },
        {
            "name": "pm-qos-warning-is-native-only-secondary-signal",
            "status": "finding" if (
                count(surface, "native_timeline", "pm_qos_duplicate") > 0
                and count(surface, "android_timeline", "pm_qos_duplicate") == 0
                and v695["cnss_retry_started"]
            ) else "review",
            "detail": {
                "native_count": count(surface, "native_timeline", "pm_qos_duplicate"),
                "android_count": count(surface, "android_timeline", "pm_qos_duplicate"),
                "native_line": native["first_lines"].get("pm_qos_duplicate", ""),
                "native_deltas_ms": native_deltas,
            },
            "next_step": "treat pm_qos as a kernel warning to track, not the first repair target unless Binder repair fails",
        },
        {
            "name": "timing-favors-cnss-daemon-continuation",
            "status": "finding" if (
                android_deltas.get("cnss_daemon_netlink_to_wlfw_start_ms") is not None
                and v695["cnss_binder_tx"] > 0
                and v695["wlfw_start"] == 0
            ) else "review",
            "detail": {
                "android_netlink_to_wlfw_ms": android_deltas.get("cnss_daemon_netlink_to_wlfw_start_ms"),
                "native_netlink_to_binder_fail_ms": native_deltas.get("cnss_daemon_netlink_to_binder_fail_ms"),
                "native_netlink_to_wlfw_ms": native_deltas.get("cnss_daemon_netlink_to_wlfw_start_ms"),
            },
            "next_step": "next live unit should target cnss-daemon Binder/runtime continuation, not Wi-Fi HAL or direct QCA writes",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v696-post-provider-retry-blocker-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V696 host-only classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v696-post-provider-retry-blocker-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh missing evidence before planning another live unit",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    primary_required = {
        "android-reference-reaches-wlfw-bdf-fwready",
        "native-stalls-after-cnss-retry-before-wlfw",
        "cnss-binder-failure-remains-native-only",
        "timing-favors-cnss-daemon-continuation",
    }
    if primary_required <= findings:
        return (
            "v696-cnss-binder-continuation-remains-primary",
            True,
            "V695 proves provider registration and fresh CNSS retry, but native still stops before WLFW while Android reaches WLFW/BDF/FW-ready without a CNSS Binder -22; the remaining primary blocker is native cnss-daemon Binder/runtime continuation, with pm_qos kept as a secondary kernel warning.",
            "plan V697 as a narrow cnss-daemon Binder/runtime repair or capture gate; keep Wi-Fi HAL, scan/connect, DHCP, and external ping blocked",
        )
    if "pm-qos-warning-is-native-only-secondary-signal" in findings:
        return (
            "v696-pm-qos-secondary-signal-needs-correlation",
            True,
            "native pm_qos warning is present, but Binder/timing evidence is not strong enough to rank the primary blocker",
            "compare more Android/native dmesg windows before another live action",
        )
    return (
        "v696-post-provider-retry-blocker-manual-review",
        False,
        "evidence did not match a known post-provider retry blocker pattern",
        "inspect V695 and Android dmesg timelines manually",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v695_manifest = load_json(args.v695_manifest)
    v695_text = read_text(args.v695_dmesg)
    android_text = read_text(args.android_dmesg)
    surface = build_surface(v695_manifest, v695_text, android_text)
    checks = [] if args.command == "plan" else build_checks(surface)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v696",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v695_manifest": str(repo_path(args.v695_manifest)),
            "v695_dmesg": str(repo_path(args.v695_dmesg)),
            "android_dmesg": str(repo_path(args.android_dmesg)),
        },
        "surface": surface,
        "checks": checks,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    surface = manifest["surface"]
    rows: list[list[str]] = []
    for side in ("android_timeline", "native_timeline"):
        counts = ((surface.get(side) or {}).get("counts") or {})
        first_ts = ((surface.get(side) or {}).get("first_ts") or {})
        for marker in (
            "service_74",
            "cnss_daemon_netlink",
            "cnss_binder_fail",
            "pm_qos_duplicate",
            "wlfw_start",
            "wlfw_service_request",
            "service_ind_wlan_pd",
            "qmi_server_connected",
            "bdf_regdb",
            "bdf_bdwlan",
            "wlan_fw_ready",
            "wlan0",
        ):
            rows.append([side, marker, str(counts.get(marker, 0)), str(first_ts.get(marker, ""))])
    delta_rows: list[list[str]] = []
    for side in ("android_deltas_ms", "native_deltas_ms"):
        for key, value in sorted((surface.get(side) or {}).items()):
            delta_rows.append([side, key, "" if value is None else str(value)])
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V696 Post-provider CNSS Retry Blocker Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## Timeline Markers",
        "",
        markdown_table(["side", "marker", "count", "first_ts"], rows),
        "",
        "## Deltas",
        "",
        markdown_table(["side", "delta", "ms"], delta_rows),
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
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
