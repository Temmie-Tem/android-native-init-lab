#!/usr/bin/env python3
"""v283 bounded CNSS start-only ICNSS/WLFW readiness delta observer."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402
import wifi_cnss_start_only_runner as start_runner  # noqa: E402
import wifi_icnss_wlfw_readiness_surface as surface  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v283-icnss-wlfw-start-delta")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def runner_args(args: argparse.Namespace, mode: str, out_dir: Path) -> argparse.Namespace:
    approved = (
        mode == "run"
        and args.allow_daemon_start
        and args.assume_yes
        and args.i_understand_reboot_only_recovery
    )
    return argparse.Namespace(
        out_dir=out_dir,
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        expect_version=args.expect_version,
        helper=args.helper,
        helper_sha256=args.helper_sha256,
        max_runtime_sec=args.max_runtime_sec,
        command=mode,
        allow_daemon_start=approved,
        assume_yes=approved,
        i_understand_reboot_only_recovery=approved,
    )


def surface_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        out_dir=args.out_dir,
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        expect_version=args.expect_version,
        toybox=args.toybox,
        command="run",
    )


def capture_surface_snapshot(args: argparse.Namespace, out_dir: Path, label: str) -> dict[str, Any]:
    store = EvidenceStore(out_dir / "snapshots" / label)
    sa = surface_args(args)
    surface.validate_no_denied_commands(sa)
    capture_list, raw_texts = surface.capture_commands(sa, store)
    captures = surface.by_name(capture_list)
    classification = surface.build_classification(captures, raw_texts)
    checks = surface.build_checks(sa, captures, raw_texts, classification)
    pass_ok, decision, reason = surface.classify(checks, classification)
    snapshot = {
        "label": label,
        "created": now_iso(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "classification": classification,
        "checks": checks,
        "captures": capture_list,
    }
    store.write_json("snapshot.json", snapshot)
    store.write_text("summary.md", surface.render_summary({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "packet_transmission": False,
        "qmi_payload": False,
        "daemon_execution": False,
        "sysfs_write": False,
        "source_references": list(surface.SOURCE_REFERENCES),
        "classification": classification,
        "checks": checks,
        "guardrails": [
            "snapshot-only: no daemon/service start",
            "snapshot-only: no QRTR nameservice packet or QMI payload",
            "snapshot-only: no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "snapshot-only: no sysfs/debugfs/configfs/control writes",
        ],
    }))
    return snapshot


def normalise(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalise(val) for key, val in sorted(value.items())}
    if isinstance(value, list):
        return [normalise(item) for item in value]
    return value


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_c = before["classification"]
    after_c = after["classification"]
    watched_fields = (
        "icnss_driver_device_present",
        "qca6390_driver_present",
        "wlan_module_loaded",
        "wlan_params",
        "icnss_module_params",
        "debugfs_mounted",
        "debug_icnss_present",
        "debugfs_readiness_candidates",
        "sysfs_readiness_candidates",
        "shutdown_wlan_readable",
        "shutdown_wlan_text",
        "dmesg_readiness_count",
        "dmesg_readiness_tail",
        "dmesg_relevant_count",
        "wlan_netdev_present",
        "wiphy_present",
    )
    deltas: list[dict[str, Any]] = []
    for field in watched_fields:
        left = normalise(before_c.get(field))
        right = normalise(after_c.get(field))
        if left != right:
            deltas.append({"field": field, "before": left, "after": right})
    before_proc = before_c.get("process_summary") or {}
    after_proc = after_c.get("process_summary") or {}
    for field in ("target_process_count", "target_running_count", "target_zombie_count", "clean"):
        left = before_proc.get(field)
        right = after_proc.get(field)
        if left != right:
            deltas.append({"field": f"process_summary.{field}", "before": left, "after": right})
    readiness_delta_fields = {
        "debugfs_readiness_candidates",
        "sysfs_readiness_candidates",
        "shutdown_wlan_readable",
        "shutdown_wlan_text",
        "dmesg_readiness_count",
        "dmesg_readiness_tail",
        "wlan_netdev_present",
        "wiphy_present",
    }
    return {
        "delta_count": len(deltas),
        "deltas": deltas,
        "readiness_delta": any(item["field"] in readiness_delta_fields for item in deltas),
        "postflight_readiness_visible": bool(after_c.get("wlan_netdev_present") or after_c.get("wiphy_present")),
        "postflight_process_clean": bool((after_c.get("process_summary") or {}).get("clean")),
        "dmesg_readiness_delta": before_c.get("dmesg_readiness_tail") != after_c.get("dmesg_readiness_tail"),
        "sysfs_candidate_delta": before_c.get("sysfs_readiness_candidates") != after_c.get("sysfs_readiness_candidates"),
        "debugfs_candidate_delta": before_c.get("debugfs_readiness_candidates") != after_c.get("debugfs_readiness_candidates"),
    }


def critical_failures(snapshot: dict[str, Any]) -> list[str]:
    return [
        str(item.get("name"))
        for item in snapshot.get("checks", [])
        if item.get("severity") == "critical" and not item.get("pass")
    ]


def start_mode_for_command(command: str) -> str:
    if command == "plan":
        return "plan"
    if command == "preflight":
        return "preflight"
    return "run"


def classify(manifest: dict[str, Any]) -> tuple[bool, str, str]:
    if manifest["mode"] == "plan":
        if not manifest["start_runner"].get("pass"):
            return False, "icnss-wlfw-start-delta-blocked", "start-only runner plan gate failed"
        return True, "icnss-wlfw-start-delta-plan-ready", "no live daemon execution; start-only runner plan is ready"
    before = manifest.get("before")
    if before is None:
        return False, "icnss-wlfw-start-delta-incomplete", "missing before snapshot"
    before_failures = critical_failures(before)
    if before_failures:
        return False, "icnss-wlfw-start-delta-incomplete", "before snapshot critical checks failed: " + ", ".join(before_failures)
    if manifest["mode"] == "preflight":
        if not manifest["start_runner"].get("pass"):
            return False, "icnss-wlfw-start-delta-blocked", "start-only runner preflight failed"
        return True, "icnss-wlfw-start-delta-preflight-ready", "read-only readiness snapshot and start-only preflight passed"
    start_manifest = manifest["start_runner"]
    if not start_manifest.get("pass"):
        return False, "icnss-wlfw-start-delta-start-failed", "start-only runner did not pass cleanup/safety gate"
    if start_manifest.get("decision") != "start-only-pass":
        return False, "icnss-wlfw-start-delta-not-observed", "start-only runner did not reach observable start-only-pass"
    after = manifest.get("after")
    if after is None:
        return False, "icnss-wlfw-start-delta-incomplete", "missing after snapshot"
    after_failures = critical_failures(after)
    if after_failures:
        return False, "icnss-wlfw-start-delta-postflight-failed", "after snapshot critical checks failed: " + ", ".join(after_failures)
    comparison = manifest.get("comparison", {})
    if comparison.get("postflight_readiness_visible"):
        return False, "icnss-wlfw-start-delta-readiness-leak", "postflight WLAN netdev/wiphy became visible"
    if not comparison.get("postflight_process_clean"):
        return False, "icnss-wlfw-start-delta-process-leak", "postflight CNSS process table is not clean"
    if comparison.get("dmesg_readiness_delta"):
        return True, "icnss-wlfw-start-readiness-log-delta-cleaned", "bounded start-only produced readiness log delta and cleaned up"
    if comparison.get("debugfs_candidate_delta") or comparison.get("sysfs_candidate_delta"):
        return True, "icnss-wlfw-start-readiness-surface-delta-cleaned", "bounded start-only changed readiness candidate surfaces and cleaned up"
    if comparison.get("readiness_delta"):
        return True, "icnss-wlfw-start-readiness-delta-cleaned", "bounded start-only changed readiness evidence and cleaned up"
    return True, "icnss-wlfw-start-no-readiness-delta", "bounded start-only completed safely with no ICNSS/WLFW readiness delta"


def render_summary(manifest: dict[str, Any]) -> str:
    rows = []
    if manifest.get("before"):
        before = manifest["before"]["classification"]
        rows.extend([
            ["before dmesg readiness", str(before.get("dmesg_readiness_count"))],
            ["before sysfs candidates", str(len(before.get("sysfs_readiness_candidates") or []))],
            ["before debugfs candidates", str(len(before.get("debugfs_readiness_candidates") or []))],
            ["before wlan netdev", str(before.get("wlan_netdev_present"))],
            ["before wiphy", str(before.get("wiphy_present"))],
        ])
    if manifest.get("after"):
        after = manifest["after"]["classification"]
        rows.extend([
            ["after dmesg readiness", str(after.get("dmesg_readiness_count"))],
            ["after sysfs candidates", str(len(after.get("sysfs_readiness_candidates") or []))],
            ["after debugfs candidates", str(len(after.get("debugfs_readiness_candidates") or []))],
            ["after wlan netdev", str(after.get("wlan_netdev_present"))],
            ["after wiphy", str(after.get("wiphy_present"))],
        ])
    comparison = manifest.get("comparison") or {"deltas": []}
    delta_rows = [
        [item["field"], json.dumps(item["before"], sort_keys=True), json.dumps(item["after"], sort_keys=True)]
        for item in comparison.get("deltas", [])
    ]
    start_observation = manifest["start_runner"].get("start_observation") or {}
    start_keys = start_observation.get("cnss_start") or {}
    lines = [
        "# ICNSS/WLFW Start-Only Delta Observer\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- mode: `{manifest['mode']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: {manifest['reason']}\n",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`\n",
        f"- packet_transmission: `{manifest['packet_transmission']}`\n",
        f"- qmi_payload: `{manifest['qmi_payload']}`\n",
        f"- sysfs_write: `{manifest['sysfs_write']}`\n\n",
        "## Snapshot Summary\n\n",
        markdown_table(["field", "value"], rows if rows else [["none", "plan-only"]]),
        "\n\n## Deltas\n\n",
        markdown_table(["field", "before", "after"], delta_rows if delta_rows else [["none", "", ""]]),
        "\n\n## Start-Only Runner\n\n",
        f"- decision: `{manifest['start_runner'].get('decision')}`\n",
        f"- pass: `{manifest['start_runner'].get('pass')}`\n",
        f"- reason: {manifest['start_runner'].get('reason')}\n",
        f"- helper result: `{start_observation.get('helper_result')}`\n",
        f"- child started: `{start_observation.get('child_started')}`\n",
        f"- observed pid: `{start_keys.get('pid', '-')}`\n",
        f"- observed pgid: `{start_keys.get('pgid', '-')}`\n",
        f"- reaped: `{start_observation.get('reaped')}`\n",
        f"- postflight safe: `{start_observation.get('postflight_safe')}`\n\n",
        "## Guardrails\n\n",
    ]
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    start_out_dir = args.start_out_dir if args.start_out_dir else args.out_dir / "cnss-start-only-run"
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    comparison: dict[str, Any] | None = None
    if args.command in {"preflight", "run"}:
        before = capture_surface_snapshot(args, out_dir, "before")
    start_manifest = start_runner.build_manifest(
        runner_args(args, start_mode_for_command(args.command), start_out_dir),
        start_mode_for_command(args.command),
    )
    if args.command == "run":
        after = capture_surface_snapshot(args, out_dir, "after")
        comparison = compare_snapshots(before, after) if before else None
    manifest = {
        "created": now_iso(),
        "mode": args.command,
        "pass": False,
        "decision": "pending",
        "reason": "pending",
        "out_dir": str(out_dir),
        "host_metadata": collect_host_metadata(),
        "packet_transmission": False,
        "qmi_payload": False,
        "daemon_start_executed": bool(start_manifest.get("daemon_start_executed")),
        "sysfs_write": False,
        "before": before,
        "after": after,
        "comparison": comparison,
        "start_runner": {
            "out_dir": start_manifest.get("out_dir"),
            "pass": start_manifest.get("pass"),
            "decision": start_manifest.get("decision"),
            "reason": start_manifest.get("reason"),
            "daemon_start_executed": start_manifest.get("daemon_start_executed"),
            "start_observation": start_manifest.get("start_observation"),
        },
        "guardrails": [
            "CNSS daemon start-only is delegated to wifi_cnss_start_only_runner explicit run gate",
            "no QRTR nameservice packet transmission",
            "no QMI request payload",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no cnss_diag",
            "no rfkill unblock or ICNSS bind/unbind",
            "no sysfs/control writes outside the start-only helper private namespace setup",
            "postflight requires no cnss target process and no wlan/wiphy readiness surface",
        ],
    }
    pass_ok, decision, reason = classify(manifest)
    manifest["pass"] = pass_ok
    manifest["decision"] = decision
    manifest["reason"] = reason
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"out_dir: {out_dir}")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--start-out-dir", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=start_runner.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=start_runner.DEFAULT_HELPER_SHA256)
    parser.add_argument("--max-runtime-sec", type=int, default=start_runner.DEFAULT_HELPER_TIMEOUT_SEC)
    parser.add_argument("--toybox", default=surface.DEFAULT_TOYBOX)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--allow-daemon-start", action="store_true")
    run_parser.add_argument("--assume-yes", action="store_true")
    run_parser.add_argument("--i-understand-reboot-only-recovery", action="store_true")
    args = parser.parse_args()
    if args.max_runtime_sec < 1 or args.max_runtime_sec > 30:
        raise SystemExit("--max-runtime-sec must be 1..30")
    if args.command != "run":
        args.allow_daemon_start = False
        args.assume_yes = False
        args.i_understand_reboot_only_recovery = False
    if args.command == "run" and not (
        args.allow_daemon_start
        and args.assume_yes
        and args.i_understand_reboot_only_recovery
    ):
        raise SystemExit("run requires --allow-daemon-start --assume-yes --i-understand-reboot-only-recovery")
    return args


def main() -> int:
    manifest = build_manifest(parse_args())
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
