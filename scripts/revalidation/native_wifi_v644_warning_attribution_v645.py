#!/usr/bin/env python3
"""V645 host-only V644 warning attribution classifier.

Compares V619, V627, V642, and V644 dmesg deltas to classify whether the V644
pm_qos warning is caused by clean-DSP state alone, service 180 alone, or the
new service 74 publication window. No device command is executed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v645-v644-warning-attribution")
DEFAULT_V619 = Path("tmp/wifi/v619-android-order-post-sysmon-observer-run/manifest.json")
DEFAULT_V627 = Path("tmp/wifi/v627-post-180-observer-live-v2/manifest.json")
DEFAULT_V642 = Path("tmp/wifi/v642-live-20260523-070145/manifest.json")
DEFAULT_V644 = Path("tmp/wifi/v644-live-20260523-071610/manifest.json")

TS_RE = re.compile(r"^\x1b\[[0-9;]*[A-Za-z]?\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]|^\[\s*(?P<plain>[0-9]+(?:\.[0-9]+)?)\]")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_qmi", re.compile(r"sysmon-qmi", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|pm_qos_add_request|kernel/power/qos\.c:616", re.I)),
)


@dataclass(frozen=True)
class RunSummary:
    label: str
    path: str
    exists: bool
    decision: str
    pass_ok: bool
    order: str
    child_started: int
    cnss_children: bool
    counts: dict[str, int]
    first_ts: dict[str, float | None]
    service74_to_warning_ms: float | None
    service180_to_warning_ms: float | None
    mdm3_after_companion: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v619", type=Path, default=DEFAULT_V619)
    parser.add_argument("--v627", type=Path, default=DEFAULT_V627)
    parser.add_argument("--v642", type=Path, default=DEFAULT_V642)
    parser.add_argument("--v644", type=Path, default=DEFAULT_V644)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    data["exists"] = True
    data["path"] = str(resolved)
    return data


def int_value(value: object) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def line_ts(line: str) -> float | None:
    clean = ANSI_RE.sub("", line).strip()
    match = re.match(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\]", clean)
    if not match:
        return None
    return float(match.group(1))


def event_summary(text: str) -> tuple[dict[str, int], dict[str, float | None]]:
    counts = {name: 0 for name, _ in PATTERNS}
    first_ts = {name: None for name, _ in PATTERNS}
    for line in text.splitlines():
        for name, pattern in PATTERNS:
            if not pattern.search(line):
                continue
            counts[name] += 1
            if first_ts[name] is None:
                first_ts[name] = line_ts(line)
    return counts, first_ts


def post_180_counts(live: dict[str, Any]) -> dict[str, int]:
    counts = {key: int_value(value) for key, value in ((live.get("markers") or {}).get("counts") or {}).items()}
    counts.update({key: int_value(value) for key, value in (live.get("v644_counts") or {}).items()})
    counts.update({key: int_value(value) for key, value in (((live.get("post_180_observer") or {}).get("counts")) or {}).items()})
    return counts


def summarize(label: str, manifest: dict[str, Any]) -> RunSummary:
    live = manifest.get("live") or {}
    keys = live.get("companion_keys") or {}
    text = str(live.get("dmesg_delta") or "")
    counts, first_ts = event_summary(text)
    for key, value in post_180_counts(live).items():
        if key in counts:
            counts[key] = max(counts[key], value)
    order = str(keys.get("wifi_companion_start.order") or "")
    service74_ts = first_ts.get("service_notifier_74")
    service180_ts = first_ts.get("service_notifier_180")
    warning_ts = first_ts.get("kernel_warning")
    return RunSummary(
        label=label,
        path=str(manifest.get("path", "")),
        exists=bool(manifest.get("exists")),
        decision=str(manifest.get("decision", "")),
        pass_ok=bool(manifest.get("pass")),
        order=order,
        child_started=int_value(keys.get("wifi_companion_start.child_started")),
        cnss_children="cnss_diag" in order or "cnss_daemon" in order,
        counts=counts,
        first_ts=first_ts,
        service74_to_warning_ms=round((warning_ts - service74_ts) * 1000, 3) if warning_ts is not None and service74_ts is not None else None,
        service180_to_warning_ms=round((warning_ts - service180_ts) * 1000, 3) if warning_ts is not None and service180_ts is not None else None,
        mdm3_after_companion=str(live.get("mdm3_after_companion") or ""),
    )


def decide(runs: dict[str, RunSummary]) -> tuple[str, bool, str, str]:
    missing = [label for label, run in runs.items() if not run.exists]
    if missing:
        return "v645-evidence-missing", False, "missing manifests: " + ",".join(missing), "restore evidence before next gate"

    v642_clean_no_warning = runs["v642"].counts.get("kernel_warning", 0) == 0 and runs["v642"].counts.get("service_notifier_74", 0) == 0
    v627_180_no_warning = runs["v627"].counts.get("service_notifier_180", 0) > 0 and runs["v627"].counts.get("kernel_warning", 0) == 0 and runs["v627"].counts.get("service_notifier_74", 0) == 0
    v619_warning_no_74 = runs["v619"].counts.get("kernel_warning", 0) > 0 and runs["v619"].counts.get("service_notifier_74", 0) == 0
    v644_74_warning = runs["v644"].counts.get("service_notifier_74", 0) > 0 and runs["v644"].counts.get("kernel_warning", 0) > 0
    v644_warning_after_74 = runs["v644"].service74_to_warning_ms is not None and 0 <= runs["v644"].service74_to_warning_ms <= 100

    if v642_clean_no_warning and v627_180_no_warning and v619_warning_no_74 and v644_74_warning and v644_warning_after_74:
        return (
            "v645-service74-window-warning-risk-classified",
            True,
            f"clean-DSP alone and service180-only windows are warning-free, while V644 warning follows service74 by {runs['v644'].service74_to_warning_ms}ms; V619 proves warning can also occur without service74 under direct DSP/sibling path",
            "plan V646 host-only Android post-service74 timing comparison; do not repeat V644 live or start HAL/qcwlanstate",
        )
    if v644_74_warning:
        return (
            "v645-v644-warning-needs-review",
            True,
            "V644 reached service74 and warning, but comparison set is incomplete",
            "inspect V644/V627/V619 timing before live retry",
        )
    return "v645-review-required", False, "evidence does not match expected warning attribution pattern", "inspect manifests manually"


def rows(runs: dict[str, RunSummary]) -> list[list[str]]:
    output: list[list[str]] = []
    for label in ("v619", "v627", "v642", "v644"):
        run = runs[label]
        output.append([
            label,
            str(run.pass_ok),
            run.decision,
            run.order,
            str(run.child_started),
            str(run.cnss_children),
            str(run.counts.get("service_notifier_180", 0)),
            str(run.counts.get("service_notifier_74", 0)),
            str(run.counts.get("wlan_pd", 0)),
            str(run.counts.get("kernel_warning", 0)),
            str(run.service74_to_warning_ms),
            run.mdm3_after_companion,
        ])
    return output


def render_summary(manifest: dict[str, Any]) -> str:
    runs = {label: RunSummary(**data) for label, data in manifest["runs"].items()}
    return "\n".join([
        "# V645 V644 Warning Attribution Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Comparison",
        "",
        markdown_table(
            ["run", "pass", "decision", "order", "children", "cnss", "svc180", "svc74", "wlan_pd", "warning", "svc74_to_warning_ms", "mdm3"],
            rows(runs),
        ),
        "",
        "## Interpretation",
        "",
        "- V642 shows clean-DSP + no-CNSS lower companion is warning-free but stops before service-notifier.",
        "- V627 shows service `180` with CNSS children is warning-free but still lacks service `74`.",
        "- V644 shows service `74`, then a near-immediate `pm_qos` warning, with WLAN-PD/WLFW still absent.",
        "- V619 shows the warning class can also happen without service `74` when direct DSP/sibling paths are involved.",
        "",
        "## Guardrails",
        "",
        "- Host-only classifier; no device command executed.",
        "- No daemon start, HAL start, scan/connect, credentials, DHCP, route, or external ping.",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    manifests = {
        "v619": load_manifest(args.v619),
        "v627": load_manifest(args.v627),
        "v642": load_manifest(args.v642),
        "v644": load_manifest(args.v644),
    }
    runs = {label: summarize(label, manifest) for label, manifest in manifests.items()}
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v645-warning-attribution-plan-ready",
            True,
            "plan-only; no evidence classification executed",
            "run V645 classifier",
        )
    else:
        decision, pass_ok, reason, next_step = decide(runs)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "runs": {label: run.__dict__ for label, run in runs.items()},
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
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
