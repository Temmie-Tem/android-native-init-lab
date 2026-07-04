#!/usr/bin/env python3
"""Run WSTA26 scan-failure diagnostics below association.

WSTA25 proved the credentialed helper can reach native init, but the confirmed
autoconnect path failed at native scan.  This runner does not send a confirmed
request and does not run connect/DHCP/ping/public exposure.  It checks that
autoconnect is disabled, captures redacted link state, then runs a bounded
native ``wifi scan`` window to determine whether the scan engine itself still
works after the WSTA25 failure.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_wsta2_native_materialization as wsta2  # noqa: E402
import run_wsta15_handoff_scan_boundary as wsta15  # noqa: E402
import run_wsta24_native_wifi_uplink_client as wsta24  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE


def write_json(path: Path, payload: Any) -> None:
    wsta2.write_json(path, payload)


def parse_kv_record(record: dict[str, Any]) -> dict[str, str]:
    return wsta2.parse_kv(str(record.get("text", "")))


def native_is_v3387(text: str) -> bool:
    return wsta24.V3387_VERSION in text and wsta24.V3387_BUILD in text


def status_summary(record: dict[str, Any]) -> dict[str, str]:
    kv = parse_kv_record(record)
    keep = (
        "decision",
        "wlan0_present",
        "operstate",
        "carrier",
        "ipv4",
        "default_route_present",
        "supplicant.process_count",
        "ctrl_socket.kind",
        "secret_values_logged",
    )
    return {key: kv[key] for key in keep if key in kv}


def autoconnect_summary(record: dict[str, Any]) -> dict[str, str]:
    kv = parse_kv_record(record)
    keep = (
        "decision",
        "config_present",
        "config_valid",
        "autoconnect",
        "profile_valid",
        "dhcp",
        "external_ping",
        "scan_before_connect",
        "retry_count",
        "secret_values_logged",
    )
    return {key: kv[key] for key in keep if key in kv}


def direct_scan_best(result: dict[str, Any]) -> dict[str, Any]:
    return result.get("direct_scan_window", {}).get("best", {})


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    if not checks.get("native_v3387"):
        return "wsta26-blocked-v3387-not-resident"
    if not checks.get("baseline_selftest_fail_zero") or not checks.get("final_selftest_fail_zero"):
        return "wsta26-blocked-native-health"
    if not checks.get("autoconnect_disabled"):
        return "wsta26-blocked-autoconnect-left-enabled"
    if checks.get("direct_scan_engine_ok"):
        if checks.get("direct_scan_has_bss"):
            return "wsta26-direct-native-scan-visible-after-wsta25-failure"
        return "wsta26-direct-native-scan-engine-ok-zero-bss"
    return "wsta26-direct-native-scan-blocked"


def run_scan_window(args: argparse.Namespace,
                    result: dict[str, Any],
                    out_path: Path) -> dict[str, Any]:
    window: dict[str, Any] = {
        "label": "direct_scan_window",
        "scan_delay_ms": args.scan_delay_ms,
        "attempts_requested": args.scan_attempts,
        "attempt_interval_sec": args.scan_interval_sec,
        "attempts": [],
    }
    result["direct_scan_window"] = window
    write_json(out_path, result)
    for attempt in range(1, args.scan_attempts + 1):
        record = wsta15.run_scan_attempt(args, "direct_scan_window", attempt)
        window["attempts"].append(record)
        window["best"] = wsta15.best_scan(window["attempts"])
        write_json(out_path, result)
        if record["scan_summary"]["scan_engine_ok"]:
            break
        if attempt < args.scan_attempts:
            time.sleep(args.scan_interval_sec)
    window["attempts_completed"] = len(window["attempts"])
    window["best"] = wsta15.best_scan(window["attempts"])
    write_json(out_path, result)
    return window


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    best = direct_scan_best(result)
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "checks": result.get("checks", {}),
        "autoconnect_status_summary": result.get("autoconnect_status_summary", {}),
        "wifi_status_pre_summary": result.get("wifi_status_pre_summary", {}),
        "wifi_status_post_summary": result.get("wifi_status_post_summary", {}),
        "direct_scan_best": {
            "decision": best.get("decision"),
            "scan_result_count": best.get("scan_result_count"),
            "scan_engine_ok": best.get("scan_engine_ok"),
            "scan_has_bss": best.get("scan_has_bss"),
            "link_up_rc": best.get("link_up_rc"),
            "link_up_errno": best.get("link_up_errno"),
            "trigger_rc": best.get("trigger_rc"),
            "trigger_errno": best.get("trigger_errno"),
            "errno": best.get("errno"),
        },
        "safety": result.get("safety", {}),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"wsta26-scan-failure-diagnostic-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta26_result.json"
    result: dict[str, Any] = {
        "scope": "WSTA26 scan-failure diagnostic below association",
        "started_utc": ts,
        "run_dir": wsta2.rel(run_dir),
        "resident_required": {
            "version": wsta24.V3387_VERSION,
            "build": wsta24.V3387_BUILD,
        },
        "wsta25_failure_reference": wsta2.rel(args.wsta25_result) if args.wsta25_result else "",
        "safety": {
            "boot_flash": False,
            "switch_root": False,
            "confirmed_autoconnect": False,
            "wifi_association": False,
            "dhcp": False,
            "external_ping": False,
            "public_tunnel": False,
            "raw_credential_values_logged": False,
        },
    }
    write_json(out_path, result)

    result["bridge_status"] = wsta2.run_host([sys.executable, str(wsta2.BRIDGE), "status", "--json"], timeout=10.0)
    write_json(out_path, result)

    version = wsta15.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
    selftest_pre = wsta15.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
    autoconnect_status = wsta15.try_cmdv1_retry(args, ["wifi", "autoconnect", "status"], timeout=args.timeout)
    wifi_status_pre = wsta15.try_cmdv1_retry(args, ["wifi", "status"], timeout=args.timeout)
    result.update({
        "version": version,
        "selftest_pre": selftest_pre,
        "autoconnect_status": autoconnect_status,
        "autoconnect_status_summary": autoconnect_summary(autoconnect_status),
        "wifi_status_pre": wifi_status_pre,
        "wifi_status_pre_summary": status_summary(wifi_status_pre),
    })
    write_json(out_path, result)

    autoconnect_kv = parse_kv_record(autoconnect_status)
    pre_checks = {
        "native_v3387": native_is_v3387(version.get("text", "")),
        "baseline_selftest_fail_zero": wsta2.selftest_passed(selftest_pre.get("text", "")),
        "autoconnect_disabled": autoconnect_kv.get("autoconnect") == "0"
        and autoconnect_kv.get("decision") == "wifi-autoconnect-disabled",
    }
    result["checks"] = pre_checks
    write_json(out_path, result)
    if not pre_checks["native_v3387"] or not pre_checks["baseline_selftest_fail_zero"] or not pre_checks["autoconnect_disabled"]:
        selftest_post = wsta15.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
        result["selftest_post"] = selftest_post
        result["checks"]["final_selftest_fail_zero"] = wsta2.selftest_passed(selftest_post.get("text", ""))
        result["decision"] = classify(result)
        result["ended_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        write_json(out_path, result)
        return result

    run_scan_window(args, result, out_path)

    wifi_status_post = wsta15.try_cmdv1_retry(args, ["wifi", "status"], timeout=args.timeout)
    selftest_post = wsta15.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
    best = direct_scan_best(result)
    result.update({
        "wifi_status_post": wifi_status_post,
        "wifi_status_post_summary": status_summary(wifi_status_post),
        "selftest_post": selftest_post,
    })
    result["checks"].update({
        "direct_scan_engine_ok": bool(best.get("scan_engine_ok")),
        "direct_scan_has_bss": bool(best.get("scan_has_bss")),
        "final_selftest_fail_zero": wsta2.selftest_passed(selftest_post.get("text", "")),
    })
    result["decision"] = classify(result)
    result["ended_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta25-result", type=Path)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=12.0)
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
        payload = {"decision": "wsta26-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if str(result.get("decision", "")).startswith("wsta26-direct-native-scan") else 2


if __name__ == "__main__":
    raise SystemExit(main())
