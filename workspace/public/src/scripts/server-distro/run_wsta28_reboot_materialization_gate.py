#!/usr/bin/env python3
"""Run WSTA28 no-flash reboot plus materialization gate.

WSTA27 showed same-boot materialization cannot recover the stale WLAN state.
This runner performs the next bounded step: with an explicit live flag, ask the
resident native shell to reboot, reacquire the bridge, verify V3387 health, then
run the WSTA27 materialization/scan gate.  It does not flash and does not run a
connect request, DHCP, ping, or public exposure.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = SCRIPT_DIR.parent / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_repl_resident_session as resident  # noqa: E402
import run_wsta2_native_materialization as wsta2  # noqa: E402
import run_wsta24_native_wifi_uplink_client as wsta24  # noqa: E402
import run_wsta26_scan_failure_diagnostic as wsta26  # noqa: E402
import run_wsta27_materialization_preflight as wsta27  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE


def write_json(path: Path, payload: Any) -> None:
    wsta2.write_json(path, payload)


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.allow_native_reboot:
        return False, "wsta28-blocked-explicit-native-reboot-allow-required"
    return True, "ok"


def wsta27_args(args: argparse.Namespace, run_dir: Path, attempt: int) -> Namespace:
    return Namespace(
        allow_materialization_live=True,
        run_id=None,
        run_dir=run_dir / f"wsta27-after-reboot-attempt-{attempt:02d}",
        bridge_host=args.host,
        bridge_port=args.port,
        timeout=args.timeout,
        probe_timeout_ms=args.probe_timeout_ms,
        scan_delay_ms=args.scan_delay_ms,
        scan_slack_sec=args.scan_slack_sec,
        scan_interval_sec=args.scan_interval_sec,
        scan_attempts=args.scan_attempts,
        print_full_json=False,
    )


def nested_wsta27_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = wsta27.public_summary(payload)
    return {
        "decision": summary.get("decision"),
        "checks": summary.get("checks", {}),
        "iftype_probe_summary": summary.get("iftype_probe_summary", {}),
        "scan_best": summary.get("scan_best", {}),
        "wifi_status_before_summary": summary.get("wifi_status_before_summary", {}),
        "wifi_status_after_summary": summary.get("wifi_status_after_summary", {}),
    }


def run_nested_wsta27(args: argparse.Namespace,
                      run_dir: Path,
                      result: dict[str, Any],
                      out_path: Path) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    result["wsta27_after_reboot_attempts"] = attempts
    for attempt in range(1, args.wsta27_attempts + 1):
        if attempt > 1 or args.post_reboot_settle_sec > 0:
            time.sleep(args.wsta27_retry_delay_sec if attempt > 1 else args.post_reboot_settle_sec)
        nested = wsta27.run(wsta27_args(args, run_dir, attempt))
        attempts.append({
            "attempt": attempt,
            "decision": nested.get("decision"),
            "summary": nested_wsta27_summary(nested),
            "run_dir": nested.get("run_dir"),
        })
        result["wsta27_after_reboot"] = nested
        write_json(out_path, result)
        if nested.get("decision") != "wsta27-blocked-native-health":
            return nested
    return result.get("wsta27_after_reboot", {})


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    if not checks.get("explicit_live_gate"):
        return result.get("gate_decision", "wsta28-blocked-explicit-live-gate")
    if not checks.get("post_reboot_health"):
        return "wsta28-blocked-post-reboot-health"
    nested = result.get("wsta27_after_reboot", {})
    if nested.get("decision") == "wsta27-materialization-scan-gate-pass":
        return "wsta28-reboot-materialization-scan-gate-pass"
    if nested.get("decision") == "wsta27-materialization-scan-engine-ok-zero-bss":
        return "wsta28-reboot-materialization-scan-engine-ok-zero-bss"
    return "wsta28-reboot-materialization-still-blocked"


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "checks": result.get("checks", {}),
        "reboot_send": {
            "accepted_no_end_marker": result.get("reboot_send", {}).get("accepted_no_end_marker"),
            "transport_error_present": bool(result.get("reboot_send", {}).get("transport_error")),
        },
        "post_reboot_health_summary": result.get("post_reboot_health_summary", {}),
        "wsta27_after_reboot": nested_wsta27_summary(result.get("wsta27_after_reboot", {})),
        "safety": result.get("safety", {}),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"wsta28-reboot-materialization-gate-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta28_result.json"

    gate_ok, gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA28 no-flash reboot plus materialization gate",
        "started_utc": ts,
        "run_dir": wsta2.rel(run_dir),
        "resident_required": {
            "supported": wsta24.SUPPORTED_UPLINK_NATIVE_BUILDS,
        },
        "gate_decision": gate_decision,
        "safety": {
            "boot_flash": False,
            "native_reboot": gate_ok,
            "switch_root": False,
            "service_connect_request": False,
            "wifi_association": False,
            "dhcp": False,
            "external_ping": False,
            "public_tunnel": False,
            "raw_credential_values_logged": False,
        },
        "checks": {"explicit_live_gate": gate_ok},
    }
    write_json(out_path, result)
    if not gate_ok:
        result["decision"] = classify(result)
        write_json(out_path, result)
        return result

    resident.send_warm_reboot(args, run_dir, 1)
    reboot_path = run_dir / "batch-001-warm-reboot-send.json"
    if reboot_path.is_file():
        result["reboot_send"] = json.loads(reboot_path.read_text(encoding="utf-8"))
    write_json(out_path, result)

    health = resident.restart_bridge_and_wait_health(args, run_dir, "wsta28")
    result["post_reboot_health"] = health
    result["post_reboot_health_summary"] = {
        key: {
            "rc": value.get("rc"),
            "status": value.get("status"),
            "contains_supported_native": wsta26.native_is_v3387(str(value.get("text", ""))),
            "selftest_fail_zero": "fail=0" in str(value.get("text", "")),
        }
        for key, value in health.get("commands", {}).items()
    }
    result["checks"]["post_reboot_health"] = (
        result["post_reboot_health_summary"].get("version", {}).get("contains_supported_native") is True
        and result["post_reboot_health_summary"].get("selftest", {}).get("selftest_fail_zero") is True
    )
    write_json(out_path, result)

    nested = run_nested_wsta27(args, run_dir, result, out_path)
    result["wsta27_after_reboot"] = nested
    result["checks"]["wsta27_after_reboot_pass"] = nested.get("decision") == "wsta27-materialization-scan-gate-pass"
    result["decision"] = classify(result)
    result["ended_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-native-reboot", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--warm-reboot-command-timeout", type=float, default=8.0)
    parser.add_argument("--warm-reboot-total-timeout", type=float, default=120.0)
    parser.add_argument("--warm-reboot-poll-sec", type=float, default=2.0)
    parser.add_argument("--bridge-restart-timeout", type=float, default=12.0)
    parser.add_argument("--health-retries", type=int, default=3)
    parser.add_argument("--health-timeout", type=float, default=12.0)
    parser.add_argument("--post-reboot-settle-sec", type=float, default=5.0)
    parser.add_argument("--wsta27-attempts", type=int, default=2)
    parser.add_argument("--wsta27-retry-delay-sec", type=float, default=3.0)
    parser.add_argument("--probe-timeout-ms", type=int, default=220000)
    parser.add_argument("--scan-delay-ms", type=int, default=5000)
    parser.add_argument("--scan-slack-sec", type=float, default=20.0)
    parser.add_argument("--scan-interval-sec", type=float, default=8.0)
    parser.add_argument("--scan-attempts", type=int, default=4)
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001 - preserve diagnostic failure in stdout.
        payload = {"decision": "wsta28-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == "wsta28-reboot-materialization-scan-gate-pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
