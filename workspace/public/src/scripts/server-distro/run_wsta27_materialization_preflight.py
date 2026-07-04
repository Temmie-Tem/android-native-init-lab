#!/usr/bin/env python3
"""Run the WSTA27 V3387 WLAN materialization preflight gate.

This runner is the guard that must pass before another credentialed
autoconnect live attempt.  It never sends a service request to connect and
never runs DHCP, ping, or public exposure.  With the explicit live flag it may
run the already-bounded native iftype materialization probe, then requires a
direct native scan window to work.
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
import run_wsta26_scan_failure_diagnostic as wsta26  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE


def write_json(path: Path, payload: Any) -> None:
    wsta2.write_json(path, payload)


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.allow_materialization_live:
        return False, "wsta27-blocked-explicit-materialization-live-allow-required"
    return True, "ok"


def wifi_admin_up(record: dict[str, Any]) -> bool:
    return bool(record.get("transport_ok") and wsta2.wlan0_admin_up(record.get("text", "")))


def iftype_probe_ok(record: dict[str, Any]) -> bool:
    text = str(record.get("text", ""))
    kv = wsta2.parse_kv(text)
    return (
        bool(record.get("transport_ok"))
        and kv.get("decision") == "softap-iftype-probe-pass"
        and kv.get("link_up_errno") == "0"
        and kv.get("ap_iftype_cleanup_ok") == "1"
    )


def probe_summary(record: dict[str, Any]) -> dict[str, Any]:
    kv = wsta2.parse_kv(str(record.get("text", "")))
    keep = (
        "decision",
        "wlan0_present",
        "wlan0_wait_elapsed_ms",
        "link_up_rc",
        "link_up_errno",
        "ap_iftype_add_rc",
        "ap_iftype_cleanup_ok",
        "secret_values_logged",
    )
    return {key: kv[key] for key in keep if key in kv}


def run_scan_window_until_engine(args: argparse.Namespace,
                                 result: dict[str, Any],
                                 out_path: Path) -> dict[str, Any]:
    window: dict[str, Any] = {
        "label": "materialized_scan_window",
        "scan_delay_ms": args.scan_delay_ms,
        "attempts_requested": args.scan_attempts,
        "attempt_interval_sec": args.scan_interval_sec,
        "attempts": [],
        "stop_condition": "scan_engine_ok",
    }
    result["materialized_scan_window"] = window
    write_json(out_path, result)
    for attempt in range(1, args.scan_attempts + 1):
        record = wsta15.run_scan_attempt(args, "materialized_scan_window", attempt)
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


def scan_best(result: dict[str, Any]) -> dict[str, Any]:
    return result.get("materialized_scan_window", {}).get("best", {})


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    if not checks.get("explicit_live_gate"):
        return result.get("gate_decision", "wsta27-blocked-explicit-live-gate")
    if not checks.get("native_v3387"):
        return "wsta27-blocked-v3387-not-resident"
    if not checks.get("baseline_selftest_fail_zero") or not checks.get("final_selftest_fail_zero"):
        return "wsta27-blocked-native-health"
    if not checks.get("autoconnect_disabled"):
        return "wsta27-blocked-autoconnect-left-enabled"
    if not checks.get("iftype_probe_pass") and not checks.get("admin_up_after_preflight"):
        return "wsta27-blocked-materialization-preflight"
    if checks.get("scan_engine_ok"):
        if checks.get("scan_has_bss"):
            return "wsta27-materialization-scan-gate-pass"
        return "wsta27-materialization-scan-engine-ok-zero-bss"
    return "wsta27-materialization-scan-blocked"


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    best = scan_best(result)
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "checks": result.get("checks", {}),
        "wifi_status_before_summary": result.get("wifi_status_before_summary", {}),
        "wifi_status_after_summary": result.get("wifi_status_after_summary", {}),
        "iftype_probe_summary": result.get("iftype_probe_summary", {}),
        "scan_best": {
            "decision": best.get("decision"),
            "scan_result_count": best.get("scan_result_count"),
            "scan_engine_ok": best.get("scan_engine_ok"),
            "scan_has_bss": best.get("scan_has_bss"),
            "link_up_rc": best.get("link_up_rc"),
            "link_up_errno": best.get("link_up_errno"),
            "trigger_rc": best.get("trigger_rc"),
            "trigger_errno": best.get("trigger_errno"),
        },
        "safety": result.get("safety", {}),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"wsta27-materialization-preflight-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta27_result.json"

    gate_ok, gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA27 V3387 WLAN materialization preflight gate",
        "started_utc": ts,
        "run_dir": wsta2.rel(run_dir),
        "resident_required": {
            "version": wsta24.V3387_VERSION,
            "build": wsta24.V3387_BUILD,
        },
        "gate_decision": gate_decision,
        "safety": {
            "boot_flash": False,
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

    result["bridge_status"] = wsta2.run_host([sys.executable, str(wsta2.BRIDGE), "status", "--json"], timeout=10.0)
    write_json(out_path, result)

    version = wsta15.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
    selftest_pre = wsta15.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
    autoconnect_status = wsta15.try_cmdv1_retry(args, ["wifi", "autoconnect", "status"], timeout=args.timeout)
    wifi_status_before = wsta15.try_cmdv1_retry(args, ["wifi", "status"], timeout=args.timeout)
    autoconnect_kv = wsta2.parse_kv(str(autoconnect_status.get("text", "")))
    result.update({
        "version": version,
        "selftest_pre": selftest_pre,
        "autoconnect_status": autoconnect_status,
        "autoconnect_status_summary": wsta26.autoconnect_summary(autoconnect_status),
        "wifi_status_before": wifi_status_before,
        "wifi_status_before_summary": wsta26.status_summary(wifi_status_before),
    })
    result["checks"].update({
        "native_v3387": wsta26.native_is_v3387(version.get("text", "")),
        "baseline_selftest_fail_zero": wsta2.selftest_passed(selftest_pre.get("text", "")),
        "autoconnect_disabled": autoconnect_kv.get("autoconnect") == "0"
        and autoconnect_kv.get("decision") == "wifi-autoconnect-disabled",
        "admin_up_before_preflight": wifi_admin_up(wifi_status_before),
    })
    write_json(out_path, result)

    if result["checks"]["native_v3387"] and result["checks"]["baseline_selftest_fail_zero"] and result["checks"]["autoconnect_disabled"]:
        if not result["checks"]["admin_up_before_preflight"]:
            timeout = max(args.timeout, (args.probe_timeout_ms / 1000.0) + 30.0)
            result["iftype_probe"] = wsta15.try_cmdv1_retry(
                args,
                ["wifi", "softap", "iftype-probe", str(args.probe_timeout_ms)],
                timeout=timeout,
                attempts=1,
            )
            result["iftype_probe_summary"] = probe_summary(result["iftype_probe"])
            result["checks"]["iftype_probe_pass"] = iftype_probe_ok(result["iftype_probe"])
            write_json(out_path, result)
        else:
            result["checks"]["iftype_probe_pass"] = True

        wifi_status_after = wsta15.try_cmdv1_retry(args, ["wifi", "status"], timeout=args.timeout)
        result["wifi_status_after"] = wifi_status_after
        result["wifi_status_after_summary"] = wsta26.status_summary(wifi_status_after)
        result["checks"]["admin_up_after_preflight"] = wifi_admin_up(wifi_status_after)
        write_json(out_path, result)

        if result["checks"].get("iftype_probe_pass") or result["checks"].get("admin_up_after_preflight"):
            run_scan_window_until_engine(args, result, out_path)
            best = scan_best(result)
            result["checks"]["scan_engine_ok"] = bool(best.get("scan_engine_ok"))
            result["checks"]["scan_has_bss"] = bool(best.get("scan_has_bss"))

    selftest_post = wsta15.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
    result["selftest_post"] = selftest_post
    result["checks"]["final_selftest_fail_zero"] = wsta2.selftest_passed(selftest_post.get("text", ""))
    result["decision"] = classify(result)
    result["ended_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-materialization-live", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=12.0)
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
        payload = {"decision": "wsta27-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == "wsta27-materialization-scan-gate-pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
