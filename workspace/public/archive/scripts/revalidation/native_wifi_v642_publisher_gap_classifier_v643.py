#!/usr/bin/env python3
"""V643 host-only classifier for the V642 post-sysmon publisher gap.

The classifier compares safe native evidence around V598/V625/V627, unsafe
V619, and clean-DSP V642. It does not contact the device, mutate sysfs, start
daemons, start Wi-Fi HAL, scan/connect, use credentials, run DHCP, change
routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v643-v642-publisher-gap-classifier")
DEFAULT_V598 = Path("tmp/wifi/v598-modem-holder-wlfw-readback/manifest.json")
DEFAULT_V619 = Path("tmp/wifi/v619-android-order-post-sysmon-observer-run/manifest.json")
DEFAULT_V625 = Path("tmp/wifi/v625-fresh-v598-class-live/manifest.json")
DEFAULT_V627 = Path("tmp/wifi/v627-post-180-observer-live-v2/manifest.json")
DEFAULT_V642 = Path("tmp/wifi/v642-live-20260523-070145/manifest.json")


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
    kernel_warning: int
    qrtr_rx: int
    qrtr_tx: int
    sysmon_qmi: int
    service_notifier: int
    service_notifier_180: int
    service_notifier_74: int
    wlan_pd: int
    qmi_server_connected: int
    wlfw: int
    bdf: int
    wlan0: int
    mdm3_after_companion: str
    qmi_attempted: int


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v598", type=Path, default=DEFAULT_V598)
    parser.add_argument("--v619", type=Path, default=DEFAULT_V619)
    parser.add_argument("--v625", type=Path, default=DEFAULT_V625)
    parser.add_argument("--v627", type=Path, default=DEFAULT_V627)
    parser.add_argument("--v642", type=Path, default=DEFAULT_V642)
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


def live_counts(live: dict[str, Any]) -> dict[str, int]:
    counts = {key: int_value(value) for key, value in ((live.get("markers") or {}).get("counts") or {}).items()}
    post_180 = ((live.get("post_180_observer") or {}).get("counts") or {})
    for key, value in post_180.items():
        counts[key] = int_value(value)
    return counts


def qmi_attempted(live: dict[str, Any]) -> int:
    readback = live.get("qrtr_readback") or {}
    total = int_value(readback.get("qmi_attempted"))
    for key, value in (live.get("companion_keys") or {}).items():
        if str(key).endswith(".qmi_attempted"):
            total += int_value(value)
    return total


def summarize(label: str, manifest: dict[str, Any]) -> RunSummary:
    live = manifest.get("live") or {}
    counts = live_counts(live)
    keys = live.get("companion_keys") or {}
    order = str(keys.get("wifi_companion_start.order") or "")
    service_180 = counts.get("service_notifier_180", 0)
    service_74 = counts.get("service_notifier_74", 0)
    generic_service = counts.get("service_notifier", 0)
    return RunSummary(
        label=label,
        path=str(manifest.get("path", "")),
        exists=bool(manifest.get("exists")),
        decision=str(manifest.get("decision", "")),
        pass_ok=bool(manifest.get("pass")),
        order=order,
        child_started=int_value(keys.get("wifi_companion_start.child_started")),
        cnss_children="cnss_diag" in order or "cnss_daemon" in order,
        kernel_warning=counts.get("kernel_warning", 0),
        qrtr_rx=counts.get("qrtr_rx", 0),
        qrtr_tx=counts.get("qrtr_tx", 0),
        sysmon_qmi=max(counts.get("sysmon_qmi", 0), counts.get("sysmon_modem", 0)),
        service_notifier=max(generic_service, service_180 + service_74),
        service_notifier_180=service_180 or generic_service,
        service_notifier_74=service_74,
        wlan_pd=counts.get("wlan_pd", 0),
        qmi_server_connected=counts.get("qmi_server_connected", 0),
        wlfw=max(counts.get("wlfw", 0), counts.get("wlfw_start", 0)),
        bdf=max(counts.get("bdf", 0), counts.get("bdf_regdb", 0), counts.get("bdf_bdwlan", 0)),
        wlan0=counts.get("wlan0", 0),
        mdm3_after_companion=str(live.get("mdm3_after_companion") or ""),
        qmi_attempted=qmi_attempted(live),
    )


def decide(runs: dict[str, RunSummary]) -> tuple[str, bool, str, str]:
    missing = [label for label, run in runs.items() if not run.exists]
    if missing:
        return (
            "v643-evidence-missing",
            False,
            "missing manifests: " + ",".join(missing),
            "restore required evidence before selecting another live gate",
        )
    if runs["v642"].kernel_warning:
        return (
            "v643-v642-unsafe-review",
            False,
            "V642 has kernel warnings; do not build on it",
            "inspect V642 dmesg before continuing",
        )
    no_cnss_no_notifier = (
        runs["v642"].qrtr_tx > 0
        and runs["v642"].sysmon_qmi > 0
        and runs["v642"].service_notifier == 0
        and not runs["v642"].cnss_children
    )
    cnss_service180 = (
        runs["v625"].cnss_children
        and runs["v627"].cnss_children
        and runs["v625"].service_notifier_180 > 0
        and runs["v627"].service_notifier_180 > 0
    )
    service74_gap = (
        runs["v627"].service_notifier_74 == 0
        and runs["v627"].wlan_pd == 0
        and runs["v627"].qmi_server_connected == 0
        and runs["v627"].qmi_attempted == 0
    )
    if no_cnss_no_notifier and cnss_service180 and service74_gap:
        return (
            "v643-cnss-correlated-service180-mdm3-service74-gap",
            True,
            "V642 clean-DSP no-CNSS path reaches QRTR TX/sysmon with no notifier; V625/V627 CNSS-including path reaches service 180 only; service 74/WLAN-PD/WLFW remain absent with mdm3 OFFLINING",
            "plan V644 clean-DSP CNSS/WLFW readback replay before any HAL/scan/connect",
        )
    if no_cnss_no_notifier:
        return (
            "v643-no-cnss-notifier-gap",
            True,
            "V642 proves clean-DSP no-CNSS path is insufficient for service-notifier",
            "compare CNSS-including paths before live retry",
        )
    return (
        "v643-review-required",
        False,
        "evidence does not match expected V642/V627 relationship",
        "inspect manifests manually before another live gate",
    )


def run_rows(runs: dict[str, RunSummary]) -> list[list[str]]:
    rows: list[list[str]] = []
    for label in ("v598", "v625", "v627", "v619", "v642"):
        run = runs[label]
        rows.append([
            label,
            str(run.pass_ok),
            run.decision,
            run.order,
            str(run.child_started),
            str(run.cnss_children),
            str(run.kernel_warning),
            str(run.qrtr_tx),
            str(run.sysmon_qmi),
            str(run.service_notifier_180),
            str(run.service_notifier_74),
            str(run.wlan_pd),
            str(run.qmi_server_connected),
            run.mdm3_after_companion,
        ])
    return rows


def render_summary(manifest: dict[str, Any]) -> str:
    runs = {label: RunSummary(**data) for label, data in manifest["runs"].items()}
    return "\n".join([
        "# V643 V642 Publisher Gap Classifier",
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
            [
                "run", "pass", "decision", "order", "children", "cnss", "warning",
                "qrtr_tx", "sysmon", "svc180", "svc74", "wlan_pd", "qmi", "mdm3",
            ],
            run_rows(runs),
        ),
        "",
        "## Interpretation",
        "",
        "- V642 removes the direct DSP warning class and reaches QRTR TX/sysmon, but no service-notifier appears without CNSS children.",
        "- V598/V625/V627 include `cnss_diag,cnss_daemon` in the companion window and reproduce service-notifier `180`.",
        "- V627 still has service `74`, WLAN-PD, WLFW/QMI, BDF, and `wlan0` absent, with `mdm3=OFFLINING`.",
        "- Therefore CNSS appears correlated with service `180`, but not sufficient for service `74` or Wi-Fi readiness.",
        "",
        "## Guardrails",
        "",
        "- Host-only classifier; no device command executed.",
        "- No daemon start, HAL start, scan/connect, credential, DHCP, route, or external ping.",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    run_manifests = {
        "v598": load_manifest(args.v598),
        "v619": load_manifest(args.v619),
        "v625": load_manifest(args.v625),
        "v627": load_manifest(args.v627),
        "v642": load_manifest(args.v642),
    }
    runs = {label: summarize(label, data) for label, data in run_manifests.items()}
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v643-publisher-gap-classifier-plan-ready",
            True,
            "plan-only; no evidence classification executed",
            "run V643 classifier",
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
        "runs": {label: data.__dict__ for label, data in runs.items()},
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
