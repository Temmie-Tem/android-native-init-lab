#!/usr/bin/env python3
"""V722 host-only CNSS launch-window tradeoff classifier.

This classifier compares Android V622 timing, native V659/V660 early-CNSS
failure evidence, and native V720 provider-first late-CNSS evidence. It does
not contact the device, start daemons, start Wi-Fi HAL, scan/connect, use
credentials, run DHCP, change routes, ping externally, write sysfs, or write
boot partitions.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v722-cnss-launch-window")
DEFAULT_ANDROID_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_V659_MANIFEST = Path("tmp/wifi/v659-vndservicemanager-readiness-only-live/manifest.json")
DEFAULT_V660_MANIFEST = Path("tmp/wifi/v660-ready-cnss-retry-live/manifest.json")
DEFAULT_V720_SOURCE = Path("tmp/wifi/latest-v720-same-window-cnss2-observer.txt")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")

DMESG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.I)),
    ("sysmon_qmi", re.compile(r"sysmon-qmi", re.I)),
    ("service_locator", re.compile(r"servloc: service_locator_new_server|Service locator initialized", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("cnss_diag_netlink", re.compile(r"netlink_create.*comm:\s*cnss_diag", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_cld80211", re.compile(r"cnss-daemon.*ctrl_getfamily.*cld80211", re.I)),
    ("cnss_binder_transaction_failed", re.compile(r"cnss-daemon.*binder:.*transaction failed|cnss-daemon.*ioctl .* returned -22", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start|\\bwlfw_start\\b", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|\\bwlan_pd\\b", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected|QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\\s*:\\s*regdb\\.bin|regdb\\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\\s*:\\s*bdwlan\\.bin|bdwlan\\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready|fw_ready", re.I)),
    ("wlan0", re.compile(r"\\bwlan0\\b", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|pm_qos_add_request|Reference count mismatch", re.I)),
)

FORBIDDEN_ACTIONS = (
    "device command",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "sysfs/debugfs write",
    "esoc0 open/hold",
    "boot image or partition write",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-v622-manifest", type=Path, default=DEFAULT_ANDROID_V622_MANIFEST)
    parser.add_argument("--v659-manifest", type=Path, default=DEFAULT_V659_MANIFEST)
    parser.add_argument("--v660-manifest", type=Path, default=DEFAULT_V660_MANIFEST)
    parser.add_argument("--native-v720-source", type=Path, default=DEFAULT_V720_SOURCE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace") if resolved.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    data = json.loads(text)
    return data if isinstance(data, dict) else {}


def intish(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ready"}


def clean_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def line_ts(line: str) -> float | None:
    match = TS_RE.match(clean_line(line))
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_dmesg(text: str) -> dict[str, Any]:
    events: dict[str, list[dict[str, Any]]] = {name: [] for name, _ in DMESG_PATTERNS}
    focus: list[str] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if not line:
            continue
        matched = False
        for name, pattern in DMESG_PATTERNS:
            if pattern.search(line):
                events[name].append({"ts": line_ts(line), "line": line[:360]})
                matched = True
        if matched:
            focus.append(line[:360])
    return {
        "counts": {name: len(rows) for name, rows in events.items()},
        "first_ts": {name: rows[0]["ts"] for name, rows in events.items() if rows and rows[0]["ts"] is not None},
        "first_lines": {name: rows[0]["line"] for name, rows in events.items() if rows},
        "focus_tail": focus[-120:],
    }


def delta_ms(first_ts: dict[str, float], later: str, earlier: str) -> float | None:
    if later not in first_ts or earlier not in first_ts:
        return None
    return round((first_ts[later] - first_ts[earlier]) * 1000.0, 3)


def android_first_ts(first: dict[str, Any]) -> dict[str, float]:
    timestamps: dict[str, float] = {}
    for key, value in first.items():
        if isinstance(value, dict):
            value = value.get("timestamp")
        try:
            timestamps[str(key)] = float(value)
        except (TypeError, ValueError):
            pass
    return timestamps


def resolve_v720_root(source: Path) -> Path:
    resolved = repo_path(source)
    if resolved.is_file() and resolved.name != "manifest.json":
        text = resolved.read_text(encoding="utf-8").strip()
        if text:
            return repo_path(Path(text))
    if resolved.name == "manifest.json":
        return resolved.parent
    return resolved


def v720_dmesg_path(source: Path) -> Path:
    root = resolve_v720_root(source)
    direct = root / "service-positive-v712" / "arm-v700-v119-provider-first-cnss" / "live" / "native" / "dmesg-delta.txt"
    if direct.exists():
        return direct
    candidates = sorted((root / "service-positive-v712").glob("arm-*/live/native/dmesg-delta.txt"))
    return candidates[0] if candidates else direct


def android_surface(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    summary = manifest.get("android_summary") if isinstance(manifest.get("android_summary"), dict) else {}
    counts = summary.get("counts") if isinstance(summary.get("counts"), dict) else {}
    deltas = summary.get("deltas_ms") if isinstance(summary.get("deltas_ms"), dict) else {}
    first_ts = android_first_ts(summary.get("first") if isinstance(summary.get("first"), dict) else {})
    return {
        "manifest": str(repo_path(path)),
        "exists": bool(manifest),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "counts": {
            "service_notifier_180": intish(counts.get("service_notifier_180")),
            "service_notifier_74": intish(counts.get("service_notifier_74")),
            "cnss_diag_netlink": intish(counts.get("cnss_diag_netlink")),
            "cnss_daemon_netlink": intish(counts.get("cnss_daemon_netlink")),
            "wlfw_start": intish(counts.get("wlfw_start")),
            "wlan_pd": intish(counts.get("wlan_pd")),
            "qmi_server_connected": intish(counts.get("qmi_server_connected")),
            "bdf_regdb": intish(counts.get("bdf_regdb")),
            "bdf_bdwlan": intish(counts.get("bdf_bdwlan")),
            "wlan_fw_ready": intish(counts.get("wlan_fw_ready")),
            "wlan0": intish(counts.get("wlan0")),
        },
        "deltas_ms": {
            "service_180_to_74": deltas.get("service_notifier_180_to_service_notifier_74")
            if deltas.get("service_notifier_180_to_service_notifier_74") is not None
            else delta_ms(first_ts, "service_notifier_74", "service_notifier_180"),
            "service_180_to_cnss_diag": deltas.get("service_notifier_180_to_cnss_diag_netlink")
            if deltas.get("service_notifier_180_to_cnss_diag_netlink") is not None
            else delta_ms(first_ts, "cnss_diag_netlink", "service_notifier_180"),
            "service_180_to_cnss_daemon": deltas.get("service_notifier_180_to_cnss_daemon_netlink")
            if deltas.get("service_notifier_180_to_cnss_daemon_netlink") is not None
            else delta_ms(first_ts, "cnss_daemon_netlink", "service_notifier_180"),
            "service_180_to_wlfw_start": deltas.get("service_notifier_180_to_wlfw_start")
            if deltas.get("service_notifier_180_to_wlfw_start") is not None
            else delta_ms(first_ts, "wlfw_start", "service_notifier_180"),
            "service_180_to_wlan_pd": deltas.get("service_notifier_180_to_wlan_pd")
            if deltas.get("service_notifier_180_to_wlan_pd") is not None
            else delta_ms(first_ts, "wlan_pd", "service_notifier_180"),
        },
    }


def manifest_counts(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    live = manifest.get("live") if isinstance(manifest.get("live"), dict) else {}
    counts = live.get("v655_counts") if isinstance(live.get("v655_counts"), dict) else {}
    return {
        "manifest": str(repo_path(path)),
        "exists": bool(manifest),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "counts": {
            "service_notifier_180": intish(counts.get("service_notifier_180")),
            "service_notifier_74": intish(counts.get("service_notifier_74")),
            "cnss_daemon_netlink": intish(counts.get("cnss_daemon_netlink")),
            "cnss_daemon_cld80211": intish(counts.get("cnss_daemon_cld80211")),
            "cnss_binder_transaction_failed": intish(counts.get("cnss_binder_transaction_failed")),
            "binder_transaction_failed": intish(counts.get("binder_transaction_failed")),
            "wlfw_start": intish(counts.get("wlfw_start")),
            "wlan_pd": intish(counts.get("wlan_pd")),
            "qmi_server_connected": intish(counts.get("qmi_server_connected")),
            "bdf_regdb": intish(counts.get("bdf_regdb")),
            "bdf_bdwlan": intish(counts.get("bdf_bdwlan")),
            "wlan_fw_ready": intish(counts.get("wlan_fw_ready")),
            "wlan0": intish(counts.get("wlan0")),
            "kernel_warning": intish(counts.get("kernel_warning")),
        },
    }


def native_provider_surface(source: Path) -> dict[str, Any]:
    dmesg_path = v720_dmesg_path(source)
    dmesg = parse_dmesg(read_text(dmesg_path))
    counts = dmesg["counts"]
    first_ts = dmesg["first_ts"]
    return {
        "dmesg": str(dmesg_path),
        "exists": dmesg_path.exists(),
        "counts": counts,
        "deltas_ms": {
            "service_180_to_74": delta_ms(first_ts, "service_notifier_74", "service_notifier_180"),
            "service_180_to_cnss_diag": delta_ms(first_ts, "cnss_diag_netlink", "service_notifier_180"),
            "service_180_to_cnss_daemon": delta_ms(first_ts, "cnss_daemon_netlink", "service_notifier_180"),
            "service_180_to_wlfw_start": delta_ms(first_ts, "wlfw_start", "service_notifier_180"),
            "service_180_to_wlan_pd": delta_ms(first_ts, "wlan_pd", "service_notifier_180"),
            "cnss_diag_to_cnss_daemon": delta_ms(first_ts, "cnss_daemon_netlink", "cnss_diag_netlink"),
        },
        "first_lines": dmesg["first_lines"],
    }


def as_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def build_checks(android: dict[str, Any],
                 v659: dict[str, Any],
                 v660: dict[str, Any],
                 provider: dict[str, Any]) -> list[dict[str, Any]]:
    android_counts = android["counts"]
    provider_counts = provider["counts"]
    provider_deltas = provider["deltas_ms"]
    android_deltas = android["deltas_ms"]
    android_daemon_ms = as_float(android_deltas.get("service_180_to_cnss_daemon"))
    android_wlfw_ms = as_float(android_deltas.get("service_180_to_wlfw_start"))
    provider_daemon_ms = as_float(provider_deltas.get("service_180_to_cnss_daemon"))
    provider_after_android_wlfw = (
        provider_daemon_ms is not None
        and android_wlfw_ms is not None
        and provider_daemon_ms > android_wlfw_ms
    )
    return [
        {
            "name": "input-evidence-ready",
            "status": "pass" if android["exists"] and v659["exists"] and v660["exists"] and provider["exists"] and android["pass"] and v659["pass"] and v660["pass"] else "blocked",
            "detail": {
                "android": android["decision"],
                "v659": v659["decision"],
                "v660": v660["decision"],
                "provider_dmesg": provider["dmesg"],
            },
            "next_step": "refresh missing evidence before routing CNSS launch timing",
        },
        {
            "name": "android-cnss-launch-window-proven",
            "status": "finding" if (
                android_counts["service_notifier_180"] > 0
                and android_counts["service_notifier_74"] > 0
                and android_counts["cnss_daemon_netlink"] > 0
                and android_counts["wlfw_start"] > 0
                and android_counts["wlan_pd"] > 0
            ) else "blocked",
            "detail": android_deltas,
            "next_step": "use Android timing as upper bound for native CNSS retry placement",
        },
        {
            "name": "early-cnss-native-binder-fails",
            "status": "finding" if (
                v659["counts"]["cnss_binder_transaction_failed"] > 0
                and v660["counts"]["cnss_binder_transaction_failed"] > 0
                and v660["counts"]["wlfw_start"] == 0
            ) else "review",
            "detail": {
                "v659_counts": v659["counts"],
                "v660_counts": v660["counts"],
            },
            "next_step": "do not simply return to the pre-provider initial CNSS path",
        },
        {
            "name": "provider-first-removes-binder-but-launches-late",
            "status": "finding" if (
                provider_counts["service_notifier_180"] > 0
                and provider_counts["service_notifier_74"] > 0
                and provider_counts["cnss_diag_netlink"] > 0
                and provider_counts["cnss_daemon_netlink"] > 0
                and provider_counts["cnss_binder_transaction_failed"] == 0
                and provider_counts["wlfw_start"] == 0
                and provider_counts["wlan_pd"] == 0
                and provider_after_android_wlfw
            ) else "review",
            "detail": {
                "provider_deltas_ms": provider_deltas,
                "android_daemon_ms": android_daemon_ms,
                "android_wlfw_ms": android_wlfw_ms,
            },
            "next_step": "test a provider-preserving but earlier CNSS retry placement before HAL/connect",
        },
        {
            "name": "service74-and-cnssdiag-not-blockers",
            "status": "pass" if provider_counts["service_notifier_74"] > 0 and provider_counts["cnss_diag_netlink"] > 0 else "blocked",
            "detail": {
                "service74": provider_counts["service_notifier_74"],
                "cnss_diag_netlink": provider_counts["cnss_diag_netlink"],
                "service_180_to_cnss_diag_ms": provider_deltas.get("service_180_to_cnss_diag"),
            },
            "next_step": "keep next gate focused on CNSS daemon placement/runtime continuation",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v722-cnss-launch-window-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V722 host-only classifier over Android, V659/V660, and V720 evidence",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v722-cnss-launch-window-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh missing evidence before another live gate",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "android-cnss-launch-window-proven",
        "early-cnss-native-binder-fails",
        "provider-first-removes-binder-but-launches-late",
    }
    if required <= findings:
        return (
            "v722-cnss-launch-window-tradeoff-classified",
            True,
            "early native CNSS paths hit the known binder failure, while provider-first suppresses that failure but starts cnss-daemon after Android would already start WLFW; service74 and cnss_diag are not the current blockers.",
            "plan V723 as a provider-preserving earlier CNSS retry placement below Wi-Fi HAL/connect",
        )
    return (
        "v722-cnss-launch-window-review",
        True,
        "evidence is valid but does not match the expected early-vs-late CNSS launch tradeoff",
        "inspect summary before selecting a live gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    delta_rows = [
        ["android", key, str(value)]
        for key, value in (manifest.get("android") or {}).get("deltas_ms", {}).items()
    ] + [
        ["provider-first", key, str(value)]
        for key, value in (manifest.get("provider_first") or {}).get("deltas_ms", {}).items()
    ]
    count_rows: list[list[str]] = []
    for source in ("android", "v659", "v660", "provider_first"):
        counts = (manifest.get(source) or {}).get("counts") or {}
        for key in (
            "service_notifier_180",
            "service_notifier_74",
            "cnss_diag_netlink",
            "cnss_daemon_netlink",
            "cnss_binder_transaction_failed",
            "binder_transaction_failed",
            "wlfw_start",
            "wlan_pd",
            "qmi_server_connected",
            "bdf_regdb",
            "bdf_bdwlan",
            "wlan_fw_ready",
            "wlan0",
            "kernel_warning",
        ):
            if key in counts:
                count_rows.append([source, key, str(counts.get(key, 0))])
    return "\n".join([
        "# V722 CNSS Launch-window Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## Timing Deltas",
        "",
        markdown_table(["source", "delta", "ms"], delta_rows),
        "",
        "## Counts",
        "",
        markdown_table(["source", "marker", "count"], count_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    android: dict[str, Any] = {}
    v659: dict[str, Any] = {}
    v660: dict[str, Any] = {}
    provider: dict[str, Any] = {}
    checks: list[dict[str, Any]] = []
    if args.command == "run":
        android = android_surface(args.android_v622_manifest)
        v659 = manifest_counts(args.v659_manifest)
        v660 = manifest_counts(args.v660_manifest)
        provider = native_provider_surface(args.native_v720_source)
        checks = build_checks(android, v659, v660, provider)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v722",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "android": android,
        "v659": v659,
        "v660": v660,
        "provider_first": provider,
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
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
