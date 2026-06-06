#!/usr/bin/env python3
"""V656 host-only service-74 regression classifier.

This classifier compares V644/V653 service-notifier positives against the V655
service-74 gate timeout. It does not contact the device, write sysfs, start
daemons, start service-manager, start Wi-Fi HAL, scan, connect, use credentials,
run DHCP, change routes, or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v656-service74-regression-classifier")
DEFAULT_V644_MANIFEST = Path("tmp/wifi/v644-live-20260523-071610/manifest.json")
DEFAULT_V653_MANIFEST = Path("tmp/wifi/v653-service74-gated-live-20260523-085337/manifest.json")
DEFAULT_V655_MANIFEST = Path("tmp/wifi/v655-vndservicemanager-cnss-retry-live/manifest.json")
DEFAULT_V653_HELPER = Path("tmp/wifi/v653-service74-gated-live-20260523-085337/native/companion-start-only-with-holder.txt")
DEFAULT_V655_HELPER = Path("tmp/wifi/v655-vndservicemanager-cnss-retry-live/native/companion-start-only-with-holder.txt")
DEFAULT_V653_V490 = Path("tmp/wifi/v653-v490-current-run/manifest.json")
DEFAULT_V655_V490 = Path("tmp/wifi/v655-v490-current-run/manifest.json")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")

MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_qmi", re.compile(r"sysmon-qmi:.*SSCTL service", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("cnss_daemon_netlink", re.compile(r"netlink_create.*comm:\s*cnss-daemon", re.I)),
    ("cnss_daemon_cld80211", re.compile(r"cnss-daemon.*ctrl_getfamily.*cld80211", re.I)),
    ("cnss_binder_transaction_failed", re.compile(r"cnss-daemon.*binder:.*transaction failed .*?-22", re.I)),
    ("wlfw_start", re.compile(r"cnss-daemon wlfw_start: Starting|\bwlfw_start\b", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin|regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin|bdwlan\.bin", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|Reference count mismatch|subsystem_put", re.I)),
)

FORBIDDEN_ACTIONS = (
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "esoc0 open",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v644-manifest", type=Path, default=DEFAULT_V644_MANIFEST)
    parser.add_argument("--v653-manifest", type=Path, default=DEFAULT_V653_MANIFEST)
    parser.add_argument("--v655-manifest", type=Path, default=DEFAULT_V655_MANIFEST)
    parser.add_argument("--v653-helper", type=Path, default=DEFAULT_V653_HELPER)
    parser.add_argument("--v655-helper", type=Path, default=DEFAULT_V655_HELPER)
    parser.add_argument("--v653-v490", type=Path, default=DEFAULT_V653_V490)
    parser.add_argument("--v655-v490", type=Path, default=DEFAULT_V655_V490)
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


def clean_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def line_time(line: str) -> float | None:
    match = TS_RE.match(clean_line(line))
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KEY_RE.match(clean_line(raw_line))
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def count_markers(text: str) -> dict[str, int]:
    counts = {name: 0 for name, _ in MARKERS}
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        for name, pattern in MARKERS:
            if pattern.search(line):
                counts[name] += 1
    return counts


def first_times(text: str) -> dict[str, float | None]:
    times = {name: None for name, _ in MARKERS}
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        timestamp = line_time(line)
        for name, pattern in MARKERS:
            if times[name] is None and pattern.search(line):
                times[name] = timestamp
    return times


def delta_ms(times: dict[str, float | None], later: str, earlier: str) -> float | None:
    later_time = times.get(later)
    earlier_time = times.get(earlier)
    if later_time is None or earlier_time is None:
        return None
    return round((later_time - earlier_time) * 1000.0, 3)


def get_counts(manifest: dict[str, Any], version_key: str) -> dict[str, int]:
    live = manifest.get("live") or {}
    counts = live.get(version_key) or live.get("v644_counts") or {}
    return {key: int(value or 0) for key, value in counts.items() if isinstance(value, int | str)}


def marker_counts(manifest: dict[str, Any]) -> dict[str, int]:
    markers = ((manifest.get("live") or {}).get("markers") or {}).get("counts") or {}
    return {key: int(value or 0) for key, value in markers.items() if isinstance(value, int | str)}


def helper_summary(text: str) -> dict[str, Any]:
    keys = parse_keys(text)
    counts = count_markers(text)
    times = first_times(text)
    return {
        "mode": keys.get("mode", ""),
        "timeout_sec": keys.get("timeout_sec", ""),
        "linkerconfig_mode": keys.get("linkerconfig_mode", ""),
        "target_profile": keys.get("target_profile", ""),
        "allow_cnss_start_only": keys.get("allow_cnss_start_only", ""),
        "allow_wifi_companion_start_only": keys.get("allow_wifi_companion_start_only", ""),
        "allow_service_manager_start_only": keys.get("allow_service_manager_start_only", ""),
        "order": keys.get("wifi_companion_start.order", ""),
        "child_started": keys.get("wifi_companion_start.child_started", ""),
        "service_manager_started": keys.get("wifi_companion_start.service_manager_started", ""),
        "service74_status": keys.get("wifi_companion_start.service74_gate.status", ""),
        "service74_seen": keys.get("wifi_companion_start.service74_gate.seen", ""),
        "service74_open": keys.get("wifi_companion_start.service74_gate.open", ""),
        "service74_wait_ms": keys.get("wifi_companion_start.service74_gate.wait_ms", ""),
        "service74_wait_limit_ms": keys.get("wifi_companion_start.service74_gate.wait_limit_ms", ""),
        "service74_baseline_count": keys.get("wifi_companion_start.service74_gate.baseline.count_74", ""),
        "service74_final_count": keys.get("wifi_companion_start.service74_gate.final.count_74", ""),
        "cnss_retry_enabled": keys.get("wifi_companion_start.cnss_retry.enabled", ""),
        "vnd_ready_enabled": keys.get("wifi_companion_start.vndservicemanager_readiness.enabled", ""),
        "counts": counts,
        "deltas_ms": {
            "qrtr_tx_to_sysmon_qmi": delta_ms(times, "sysmon_qmi", "qrtr_tx"),
            "sysmon_qmi_to_service74": delta_ms(times, "service_notifier_74", "sysmon_qmi"),
            "service74_to_kernel_warning": delta_ms(times, "kernel_warning", "service_notifier_74"),
            "sysmon_qmi_to_cnss_binder_transaction": delta_ms(times, "cnss_binder_transaction_failed", "sysmon_qmi"),
        },
    }


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def build_matrix(manifest: dict[str, Any]) -> list[list[str]]:
    v644 = manifest["v644"]
    v653 = manifest["v653"]
    v655 = manifest["v655"]
    return [
        ["service `74`", str(v644["counts"].get("service_notifier_74", 0)), str(v653["counts"].get("service_notifier_74", 0)), str(v655["counts"].get("service_notifier_74", 0)), "V655 regressed before service-manager"],
        ["service `180`", str(v644["counts"].get("service_notifier_180", 0)), str(v653["counts"].get("service_notifier_180", 0)), str(v655["counts"].get("service_notifier_180", 0)), "same publication layer as service `74`"],
        ["QRTR TX", str(v644["markers"].get("qrtr_tx", 0)), str(v653["markers"].get("qrtr_tx", 0)), str(v655["markers"].get("qrtr_tx", 0)), "lower QRTR survives"],
        ["sibling sysmon", str(v644["markers"].get("sysmon_qmi", 0)), str(v653["markers"].get("sysmon_qmi", 0)), str(v655["markers"].get("sysmon_qmi", 0)), "SSCTL layer survives"],
        ["CNSS netlink", str(v644["counts"].get("cnss_daemon_netlink", 0)), str(v653["counts"].get("cnss_daemon_netlink", 0)), str(v655["counts"].get("cnss_daemon_netlink", 0)), "cnss-daemon still starts"],
        ["CNSS binder transactions", str(v644["counts"].get("cnss_binder_transaction_failed", 0)), str(v653["counts"].get("cnss_binder_transaction_failed", 0)), str(v655["counts"].get("cnss_binder_transaction_failed", 0)), "V655 binder noise happens without service `74`"],
        ["kernel warning", str(v644["counts"].get("kernel_warning", 0)), str(v653["counts"].get("kernel_warning", 0)), str(v655["counts"].get("kernel_warning", 0)), "warning absence is not enough to recover service `74`"],
        ["Wi-Fi link", str(v644["counts"].get("wlan0", 0)), str(v653["counts"].get("wlan0", 0)), str(v655["counts"].get("wlan0", 0)), "not reached"],
    ]


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v644_manifest = load_json(args.v644_manifest)
    v653_manifest = load_json(args.v653_manifest)
    v655_manifest = load_json(args.v655_manifest)
    v653_helper = helper_summary(read_text(args.v653_helper))
    v655_helper = helper_summary(read_text(args.v655_helper))
    v653_v490 = load_json(args.v653_v490)
    v655_v490 = load_json(args.v655_v490)

    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "inputs": {
            "v644_manifest": str(repo_path(args.v644_manifest)),
            "v653_manifest": str(repo_path(args.v653_manifest)),
            "v655_manifest": str(repo_path(args.v655_manifest)),
            "v653_helper": str(repo_path(args.v653_helper)),
            "v655_helper": str(repo_path(args.v655_helper)),
            "v653_v490": str(repo_path(args.v653_v490)),
            "v655_v490": str(repo_path(args.v655_v490)),
        },
        "host": collect_host_metadata(),
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_bringup_executed": False,
        "forbidden_actions": list(FORBIDDEN_ACTIONS),
        "v644": {
            "decision": v644_manifest.get("decision", ""),
            "pass": v644_manifest.get("pass", False),
            "counts": get_counts(v644_manifest, "v644_counts"),
            "markers": marker_counts(v644_manifest),
        },
        "v653": {
            "decision": v653_manifest.get("decision", ""),
            "pass": v653_manifest.get("pass", False),
            "service_manager_start_executed": bool(v653_manifest.get("service_manager_start_executed")),
            "counts": get_counts(v653_manifest, "v653_counts"),
            "markers": marker_counts(v653_manifest),
            "helper": v653_helper,
            "v490_decision": v653_v490.get("decision", ""),
            "v490_generated_at": v653_v490.get("generated_at", ""),
        },
        "v655": {
            "decision": v655_manifest.get("decision", ""),
            "pass": v655_manifest.get("pass", False),
            "service_manager_start_executed": bool(v655_manifest.get("service_manager_start_executed")),
            "counts": get_counts(v655_manifest, "v655_counts"),
            "markers": marker_counts(v655_manifest),
            "helper": v655_helper,
            "v490_decision": v655_v490.get("decision", ""),
            "v490_generated_at": v655_v490.get("generated_at", ""),
        },
    }
    manifest["matrix_rows"] = build_matrix(manifest)
    manifest["helper_delta_rows"] = [
        ["mode", v653_helper["mode"], v655_helper["mode"], "only intentional live-mode delta before service-manager"],
        ["order", v653_helper["order"], v655_helper["order"], "V655 extends post-gate tail only"],
        ["child_started", v653_helper["child_started"], v655_helper["child_started"], "V655 stopped at gate before service-manager"],
        ["service_manager_started", v653_helper["service_manager_started"], v655_helper["service_manager_started"], "not causal for V655 loss because it was withheld"],
        ["service74_status", v653_helper["service74_status"], v655_helper["service74_status"], "primary regression"],
        ["service74_wait_ms", v653_helper["service74_wait_ms"], v655_helper["service74_wait_ms"], "V655 waited full gate window"],
        ["service74_count", str(manifest["v653"]["counts"].get("service_notifier_74", 0)), str(manifest["v655"]["counts"].get("service_notifier_74", 0)), "V653 published service `74`; V655 never did"],
        ["cnss_binder_transactions", str(manifest["v653"]["counts"].get("cnss_binder_transaction_failed", 0)), str(manifest["v655"]["counts"].get("cnss_binder_transaction_failed", 0)), "V655 loops binder before service-notifier"],
    ]
    decision, pass_ok, reason, next_step = decide(manifest)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "inferences": {
            "service74_regression_confirmed": decision == "v656-service74-regression-classified",
            "lower_qrtr_sysmon_parity": all(
                manifest["v653"]["markers"].get(key, 0) == manifest["v655"]["markers"].get(key, 0)
                for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi")
            ),
            "service_manager_not_v655_cause": not manifest["v655"]["service_manager_start_executed"],
            "v490_passed_both_runs": manifest["v653"]["v490_decision"] == "v490-selinux-policy-load-proof-pass"
            and manifest["v655"]["v490_decision"] == "v490-selinux-policy-load-proof-pass",
        },
    })
    return manifest


def decide(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest["command"] == "plan":
        return (
            "v656-service74-regression-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V656 host-only classifier",
        )
    v653_has_74 = manifest["v653"]["counts"].get("service_notifier_74", 0) > 0
    v655_lacks_74 = manifest["v655"]["counts"].get("service_notifier_74", 0) == 0
    lower_parity = all(
        manifest["v653"]["markers"].get(key, 0) == manifest["v655"]["markers"].get(key, 0)
        for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi")
    )
    v655_service_manager_withheld = not manifest["v655"]["service_manager_start_executed"]
    v490_ok = (
        manifest["v653"]["v490_decision"] == "v490-selinux-policy-load-proof-pass"
        and manifest["v655"]["v490_decision"] == "v490-selinux-policy-load-proof-pass"
    )
    if v653_has_74 and v655_lacks_74 and lower_parity and v655_service_manager_withheld and v490_ok:
        return (
            "v656-service74-regression-classified",
            True,
            "V653 reached service 74 but V655 lost service 74 despite matching QRTR/sysmon lower readiness and fresh V490; V655 withheld service-manager, so vndservicemanager readiness was not tested",
            "run a bounded V657 exact V653-mode replay with helper v106 before attempting the CNSS retry mode again",
        )
    return (
        "v656-service74-regression-review-required",
        False,
        "evidence did not match the expected V653-positive/V655-timeout regression shape",
        "inspect V653/V655 manifests and helper transcripts manually",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V656 Service74 Regression Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["subject", "V644", "V653", "V655", "interpretation"], manifest["matrix_rows"]),
        "",
        "## Helper Delta",
        "",
        markdown_table(["field", "V653", "V655", "interpretation"], manifest["helper_delta_rows"]),
        "",
        "## Inferences",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["inferences"].items()]),
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
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
