#!/usr/bin/env python3
"""v279 bounded CNSS start-only QCA6390/WLAN delta observer.

This tool wraps the existing guarded CNSS start-only runner and compares
read-only QCA6390/WLAN state before and after the bounded run.  It does not send
QRTR nameservice packets, does not send QMI payloads, and does not perform Wi-Fi
scan/connect/link-up actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402
import wifi_cnss_start_only_runner as start_runner  # noqa: E402
import wifi_qca6390_driver_param_classifier as qca  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v279-cnss-qca6390-start-delta")
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


def qca_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        expect_version=args.expect_version,
        v277_manifest=args.v277_manifest,
        toybox=args.toybox,
    )


def capture_qca_snapshot(args: argparse.Namespace, out_dir: Path, label: str) -> dict[str, Any]:
    store = EvidenceStore(out_dir / "snapshots" / label)
    qa = qca_args(args)
    qca.validate_no_denied_commands(qa)
    v277 = qca.load_json(args.v277_manifest)
    capture_list = qca.capture_commands(qa, store)
    captures = qca.by_name(capture_list)
    classification = qca.build_classification(captures, v277)
    checks = qca.build_checks(qa, captures, classification)
    pass_ok, decision, reason = qca.classify(checks, classification)
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
    return snapshot


def normalise_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalise_value(val) for key, val in sorted(value.items())}
    if isinstance(value, list):
        return [normalise_value(item) for item in value]
    return value


def compare_classification(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_c = before["classification"]
    after_c = after["classification"]
    watched_fields = (
        "qca_driver_present",
        "qca_modalias",
        "qca_compatible",
        "driver_candidates",
        "wlan_params",
        "wlan_netdev_present",
        "wiphy_present",
        "wifi_rfkill_present",
    )
    deltas: list[dict[str, Any]] = []
    for field in watched_fields:
        left = normalise_value(before_c.get(field))
        right = normalise_value(after_c.get(field))
        if left != right:
            deltas.append({"field": field, "before": left, "after": right})
    before_proc = before_c.get("process_summary") or {}
    after_proc = after_c.get("process_summary") or {}
    process_fields = ("target_process_count", "target_running_count", "target_zombie_count", "clean")
    for field in process_fields:
        left = before_proc.get(field)
        right = after_proc.get(field)
        if left != right:
            deltas.append({"field": f"process_summary.{field}", "before": left, "after": right})
    return {
        "delta_count": len(deltas),
        "deltas": deltas,
        "qca_driver_delta": before_c.get("qca_driver_present") != after_c.get("qca_driver_present"),
        "wlan_param_delta": before_c.get("wlan_params") != after_c.get("wlan_params"),
        "readiness_delta": any(
            before_c.get(field) != after_c.get(field)
            for field in ("wlan_netdev_present", "wiphy_present", "wifi_rfkill_present")
        ),
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
            return False, "cnss-qca6390-start-delta-blocked", "start-only runner plan gate failed"
        return True, "cnss-qca6390-start-delta-plan-ready", "no live daemon execution; plan and prerequisites are ready"
    before = manifest.get("before")
    if before is None:
        return False, "cnss-qca6390-start-delta-incomplete", "missing before snapshot"
    before_failures = critical_failures(before)
    if before_failures:
        return False, "cnss-qca6390-start-delta-incomplete", "before snapshot critical checks failed: " + ", ".join(before_failures)
    if manifest["mode"] == "preflight":
        if not manifest["start_runner"].get("pass"):
            return False, "cnss-qca6390-start-delta-blocked", "start-only runner preflight failed"
        return True, "cnss-qca6390-start-delta-preflight-ready", "read-only QCA snapshot and start-only preflight passed"
    start_manifest = manifest["start_runner"]
    if not start_manifest.get("pass"):
        return False, "cnss-qca6390-start-delta-start-failed", "start-only runner did not pass its cleanup/safety gate"
    after = manifest.get("after")
    if after is None:
        return False, "cnss-qca6390-start-delta-incomplete", "missing after snapshot"
    after_failures = critical_failures(after)
    if after_failures:
        return False, "cnss-qca6390-start-delta-postflight-failed", "after snapshot critical checks failed: " + ", ".join(after_failures)
    after_c = after["classification"]
    if after_c.get("wlan_netdev_present") or after_c.get("wiphy_present") or after_c.get("wifi_rfkill_present"):
        return False, "cnss-qca6390-start-delta-readiness-leak", "postflight WLAN readiness surface became visible"
    comparison = manifest.get("comparison", {})
    if comparison.get("qca_driver_delta") or comparison.get("wlan_param_delta"):
        return True, "cnss-qca6390-start-delta-observed", "bounded start-only changed QCA driver or WLAN parameter state"
    if comparison.get("readiness_delta"):
        return True, "cnss-qca6390-start-readiness-delta-cleaned", "readiness surface changed during observation but postflight is clean"
    return True, "cnss-qca6390-no-driver-delta", "bounded start-only completed safely with no QCA driver or WLAN parameter delta"


def render_summary(manifest: dict[str, Any]) -> str:
    rows = []
    if manifest.get("before"):
        before = manifest["before"]["classification"]
        rows.append(["before qca_driver_present", str(before.get("qca_driver_present"))])
        rows.append(["before wlan_params", json.dumps(before.get("wlan_params"), sort_keys=True)])
    if manifest.get("after"):
        after = manifest["after"]["classification"]
        rows.append(["after qca_driver_present", str(after.get("qca_driver_present"))])
        rows.append(["after wlan_params", json.dumps(after.get("wlan_params"), sort_keys=True)])
    comparison = manifest.get("comparison") or {"deltas": []}
    delta_rows = [
        [item["field"], json.dumps(item["before"], sort_keys=True), json.dumps(item["after"], sort_keys=True)]
        for item in comparison.get("deltas", [])
    ]
    lines = [
        "# CNSS QCA6390 Start-Only Delta Observer\n\n",
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
        f"- reason: {manifest['start_runner'].get('reason')}\n\n",
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
        before = capture_qca_snapshot(args, out_dir, "before")
    start_manifest = start_runner.build_manifest(
        runner_args(args, start_mode_for_command(args.command), start_out_dir),
        start_mode_for_command(args.command),
    )
    if args.command == "run":
        after = capture_qca_snapshot(args, out_dir, "after")
        comparison = compare_classification(before, after) if before else None
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
            "no sysfs/control writes outside the start-only helper's private namespace setup",
            "postflight requires no cnss target process and no wlan/wiphy/rfkill readiness surface",
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
    parser.add_argument("--v277-manifest", type=Path, default=qca.DEFAULT_V277_MANIFEST)
    parser.add_argument("--toybox", default=qca.DEFAULT_TOYBOX)
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
