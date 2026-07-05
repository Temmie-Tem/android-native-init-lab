#!/usr/bin/env python3
"""Run WSTA43: orchestrated WSTA28 scan-green + WSTA42 D-public gate.

WSTA42 proved native-owned STA uplink plus Debian D-public quick Tunnel, but it
needed a manual WSTA28 reboot/materialization precondition immediately before
the live run.  WSTA43 makes that precondition explicit and reproducible:

1. explicit native-reboot + credentialed Wi-Fi + public-exposure gates;
2. WSTA28 no-flash reboot/materialization scan gate;
3. WSTA42 native-owned STA uplink and quick Tunnel live gate.

The runner prints a redacted public summary.  Full nested evidence is written
only under the private run directory.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = SCRIPT_DIR.parent / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import prepare_dpublic_preflight as dpublic  # noqa: E402
import run_wsta2_native_materialization as wsta2  # noqa: E402
import run_wsta25_confirmed_autoconnect_live as wsta25  # noqa: E402
import run_wsta28_reboot_materialization_gate as wsta28  # noqa: E402
import run_wsta42_native_uplink_dpublic_tunnel as wsta42  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE
PUBLIC_CONFIRM_TOKEN = dpublic.DPUBLIC_LIVE_OPERATOR_TOKEN
PASS_DECISION = "wsta43-orchestrated-native-uplink-dpublic-pass"


def rel(path: Path) -> str:
    return wsta2.rel(path)


def write_json(path: Path, payload: Any) -> None:
    wsta2.write_json(path, payload)


def cloudflared_egress_enabled(args: argparse.Namespace) -> bool:
    return wsta42.cloudflared_egress_enabled(args)


def cloudflared_egress_dns4_values(args: argparse.Namespace) -> list[str]:
    return wsta42.cloudflared_egress_dns4_values(args)


def cloudflared_egress_tls4_values(args: argparse.Namespace) -> list[str]:
    return wsta42.cloudflared_egress_tls4_values(args)


def cloudflared_egress_gate_detail(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "enabled": cloudflared_egress_enabled(args),
        "force_proof": bool(getattr(args, "force_cloudflared_egress_allowlist_proof", False)),
        "dns4_count": len(cloudflared_egress_dns4_values(args)),
        "tls4_count": len(cloudflared_egress_tls4_values(args)),
        "route_values_redacted": True,
    }


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.allow_orchestrated_live:
        return False, "wsta43-blocked-explicit-orchestrated-live-allow-required"
    if not args.allow_native_reboot:
        return False, "wsta43-blocked-explicit-native-reboot-allow-required"
    if not args.allow_public_live:
        return False, "wsta43-blocked-explicit-public-live-allow-required"
    if not args.ack_credentialed_wifi:
        return False, "wsta43-blocked-credentialed-wifi-ack-required"
    if not args.ack_public_exposure:
        return False, "wsta43-blocked-public-exposure-ack-required"
    if not args.ack_packet_filter_mutation:
        return False, "wsta43-blocked-packet-filter-mutation-ack-required"
    if not args.force_packet_filter_restore_proof:
        return False, "wsta43-blocked-packet-filter-restore-proof-required"
    if cloudflared_egress_enabled(args):
        if not getattr(args, "force_cloudflared_egress_allowlist_proof", False):
            return False, "wsta43-blocked-cloudflared-egress-allowlist-proof-required"
        if not cloudflared_egress_dns4_values(args) or not cloudflared_egress_tls4_values(args):
            return False, "wsta43-blocked-cloudflared-egress-route-required"
    if args.native_confirm_token != wsta25.NATIVE_CONFIRM_TOKEN:
        return False, "wsta43-blocked-native-confirm-token-required"
    if args.public_confirm_token != PUBLIC_CONFIRM_TOKEN:
        return False, "wsta43-blocked-public-confirm-token-required"
    return True, "ok"


def wsta28_args(args: argparse.Namespace, run_dir: Path) -> Namespace:
    return Namespace(
        allow_native_reboot=True,
        run_id=None,
        run_dir=run_dir / "wsta28-reboot-materialization",
        host=args.bridge_host,
        port=args.bridge_port,
        timeout=args.timeout,
        warm_reboot_command_timeout=args.warm_reboot_command_timeout,
        warm_reboot_total_timeout=args.warm_reboot_total_timeout,
        warm_reboot_poll_sec=args.warm_reboot_poll_sec,
        bridge_restart_timeout=args.bridge_restart_timeout,
        health_retries=args.health_retries,
        health_timeout=args.health_timeout,
        post_reboot_settle_sec=args.post_reboot_settle_sec,
        wsta27_attempts=args.wsta27_attempts,
        wsta27_retry_delay_sec=args.wsta27_retry_delay_sec,
        probe_timeout_ms=args.probe_timeout_ms,
        scan_delay_ms=args.scan_delay_ms,
        scan_slack_sec=args.scan_slack_sec,
        scan_interval_sec=args.scan_interval_sec,
        scan_attempts=args.scan_attempts,
        print_full_json=False,
    )


def wsta42_args(args: argparse.Namespace, run_dir: Path) -> Namespace:
    nested = wsta42.build_arg_parser().parse_args([])
    nested.run_id = None
    nested.run_dir = run_dir / "wsta42-native-uplink-dpublic"
    nested.bridge_host = args.bridge_host
    nested.bridge_port = args.bridge_port
    nested.device_ip = args.device_ip
    nested.ssh_port = args.ssh_port
    nested.timeout = args.timeout
    nested.sha_timeout = args.sha_timeout
    nested.setup_timeout = args.setup_timeout
    nested.cleanup_timeout = args.cleanup_timeout
    nested.ssh_timeout = args.ssh_timeout
    nested.ssh_connect_timeout = args.ssh_connect_timeout
    nested.bridge_timeout = args.bridge_timeout
    nested.connect_timeout = args.connect_timeout
    nested.tcp_timeout = args.tcp_timeout
    nested.transfer_timeout = args.transfer_timeout
    nested.transfer_delay = args.transfer_delay
    nested.toybox = args.toybox
    nested.local_image = args.local_image
    nested.local_image_sha256 = args.local_image_sha256
    nested.remote_image = args.remote_image
    nested.remote_clean_image = args.remote_clean_image
    nested.mountpoint = args.mountpoint
    nested.cloudflared = args.cloudflared
    nested.cloudflared_stage_timeout = args.cloudflared_stage_timeout
    nested.host_resolver_conf = list(args.host_resolver_conf or [])
    nested.service_dir = args.service_dir
    nested.service_lifetime_ms = args.service_lifetime_ms
    nested.service_poll_ms = args.service_poll_ms
    nested.response_timeout_sec = args.response_timeout_sec
    nested.confirmed_timeout_sec = args.confirmed_timeout_sec
    nested.use_native_uplink_profile = args.use_native_uplink_profile
    nested.tunnel_url_wait_sec = args.tunnel_url_wait_sec
    nested.public_curl_timeout_sec = args.public_curl_timeout_sec
    nested.public_smoke_attempts = args.public_smoke_attempts
    nested.public_smoke_retry_delay_sec = args.public_smoke_retry_delay_sec
    nested.allow_public_live = True
    nested.ack_credentialed_wifi = True
    nested.ack_public_exposure = True
    nested.ack_packet_filter_mutation = True
    nested.force_packet_filter_restore_proof = True
    nested.enable_cloudflared_egress_allowlist = cloudflared_egress_enabled(args)
    nested.force_cloudflared_egress_allowlist_proof = bool(
        getattr(args, "force_cloudflared_egress_allowlist_proof", False)
    )
    nested.cloudflared_egress_dns4 = cloudflared_egress_dns4_values(args)
    nested.cloudflared_egress_tls4 = cloudflared_egress_tls4_values(args)
    nested.native_confirm_token = args.native_confirm_token
    nested.public_confirm_token = args.public_confirm_token
    nested.enable_autoconnect = True
    nested.autoconnect_profile = args.autoconnect_profile
    nested.disable_autoconnect_on_cleanup = True
    nested.sync_time = args.sync_time
    return nested


def summarize_wsta42(payload: dict[str, Any]) -> dict[str, Any]:
    public = payload.get("host_public_smoke", {})
    resolver = payload.get("resolver_sync", {})
    smoke = payload.get("smoke_start", {})
    tunnel = payload.get("cloudflared_start", {})
    url_fetch = payload.get("public_url_fetch", {})
    return {
        "decision": payload.get("decision"),
        "run_dir": payload.get("run_dir"),
        "checks": payload.get("checks", {}),
        "resolver_sync": {
            key: resolver.get(key)
            for key in (
                "ready",
                "copied",
                "source",
                "nameserver_count",
                "host_fallback_attempted",
                "host_fallback_checked_count",
                "host_fallback_source_nameserver_count",
            )
        },
        "smoke_start": {
            key: smoke.get(key)
            for key in (
                "started",
                "local_smoke_ok",
                "loopback_up_rc",
                "pid_alive",
                "listen",
                "http_get_rc",
                "returncode",
                "elapsed_sec",
            )
        },
        "cloudflared_start": {
            key: tunnel.get(key)
            for key in ("process_alive", "url_observed", "returncode", "elapsed_sec")
        },
        "public_url_fetch": {
            key: url_fetch.get(key)
            for key in ("url_observed", "url_len", "stdout_redacted", "stderr_present")
        },
        "host_public_smoke": {
            key: public.get(key)
            for key in (
                "returncode",
                "http_status",
                "marker_ok",
                "service_ok",
                "public_exposure_marker_ok",
                "url_redacted",
                "attempt_count",
                "body_len",
                "elapsed_sec",
            )
        },
        "image_prep": wsta42.image_prep_summary(payload),
        "dpublic_cleanup": {
            key: payload.get("dpublic_cleanup", {}).get(key)
            for key in ("cleaned", "returncode", "elapsed_sec")
        },
        "postcheck_parse": payload.get("postcheck_parse", {}),
    }


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    if not checks.get("explicit_live_gate"):
        return result.get("gate_decision", "wsta43-blocked-explicit-live-gate")
    if not checks.get("wsta28_scan_green"):
        return "wsta43-blocked-reboot-materialization"
    if not checks.get("wsta42_pass"):
        return "wsta43-blocked-dpublic-tunnel"
    return PASS_DECISION


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "checks": result.get("checks", {}),
        "wsta28": wsta28.public_summary(result.get("wsta28", {})),
        "wsta42": summarize_wsta42(result.get("wsta42", {})),
        "safety": result.get("safety", {}),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"wsta43-orchestrated-native-uplink-dpublic-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta43_result.json"

    gate_ok, gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA43 orchestrated reboot/materialization plus native-owned D-public tunnel",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "gate_decision": gate_decision,
        "safety": {
            "boot_flash": False,
            "native_reboot": gate_ok and args.allow_native_reboot,
            "switch_root": False,
            "userdata_touch": False,
            "wifi_connect": "native-confirm-gated",
            "dhcp_routing": "native-config-gated-after-confirmed-live",
            "external_ping": False,
            "public_tunnel": "explicit-public-live-gated",
            "native_confirm_token_value_logged": False,
            "public_confirm_token_value_logged": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
        "checks": {
            "explicit_live_gate": gate_ok,
            "allow_native_reboot": bool(args.allow_native_reboot),
            "allow_public_live": bool(args.allow_public_live),
            "ack_credentialed_wifi": bool(args.ack_credentialed_wifi),
            "ack_public_exposure": bool(args.ack_public_exposure),
            "ack_packet_filter_mutation": bool(args.ack_packet_filter_mutation),
            "force_packet_filter_restore_proof": bool(args.force_packet_filter_restore_proof),
            "cloudflared_egress_allowlist_enabled": cloudflared_egress_enabled(args),
            "force_cloudflared_egress_allowlist_proof": bool(
                getattr(args, "force_cloudflared_egress_allowlist_proof", False)
            ),
            "cloudflared_egress_dns4_count": len(cloudflared_egress_dns4_values(args)),
            "cloudflared_egress_tls4_count": len(cloudflared_egress_tls4_values(args)),
            "cloudflared_egress_route_values_redacted": True,
            "native_confirm_token_supplied": bool(args.native_confirm_token),
            "native_confirm_token_matches": args.native_confirm_token == wsta25.NATIVE_CONFIRM_TOKEN,
            "public_confirm_token_supplied": bool(args.public_confirm_token),
            "public_confirm_token_matches": args.public_confirm_token == PUBLIC_CONFIRM_TOKEN,
        },
    }
    write_json(out_path, result)
    if not gate_ok:
        result["decision"] = classify(result)
        write_json(out_path, result)
        return result

    nested_wsta28 = wsta28.run(wsta28_args(args, run_dir))
    result["wsta28"] = nested_wsta28
    result["checks"]["wsta28_scan_green"] = (
        nested_wsta28.get("decision") == "wsta28-reboot-materialization-scan-gate-pass"
    )
    write_json(out_path, result)
    if not result["checks"]["wsta28_scan_green"]:
        result["decision"] = classify(result)
        result["ended_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        write_json(out_path, result)
        return result

    nested_wsta42 = wsta42.run(wsta42_args(args, run_dir))
    result["wsta42"] = nested_wsta42
    result["checks"]["wsta42_pass"] = nested_wsta42.get("decision") == wsta42.PASS_DECISION
    result["checks"]["final_selftest_fail_zero"] = bool(
        nested_wsta42.get("checks", {}).get("final_selftest_fail_zero")
    )
    result["checks"]["public_url_value_logged"] = False
    result["checks"]["secret_values_logged"] = 0
    result["decision"] = classify(result)
    result["ended_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default=wsta42.wsta24.DEFAULT_DEVICE_IP)
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--timeout", type=float, default=20.0)
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
    parser.add_argument("--sha-timeout", type=float, default=180.0)
    parser.add_argument("--setup-timeout", type=float, default=180.0)
    parser.add_argument("--cleanup-timeout", type=float, default=120.0)
    parser.add_argument("--ssh-timeout", type=float, default=45.0)
    parser.add_argument("--ssh-connect-timeout", type=int, default=8)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--local-image", type=Path, default=wsta42.DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--local-image-sha256", default=wsta42.DEFAULT_LOCAL_IMAGE_SHA256)
    parser.add_argument("--remote-image", default=wsta42.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--remote-clean-image", default=wsta42.DEFAULT_REMOTE_CLEAN_IMAGE)
    parser.add_argument("--mountpoint", default=wsta42.d1.DEFAULT_MOUNTPOINT)
    parser.add_argument("--cloudflared", type=Path, default=dpublic.DEFAULT_CLOUDFLARED)
    parser.add_argument("--cloudflared-stage-timeout", type=float, default=180.0)
    parser.add_argument("--host-resolver-conf", type=Path, action="append", default=[])
    parser.add_argument("--service-dir", default="/tmp/a90-native-wifi-uplink-service")
    parser.add_argument("--service-lifetime-ms", type=int, default=360000)
    parser.add_argument("--service-poll-ms", type=int, default=100)
    parser.add_argument("--response-timeout-sec", type=int, default=30)
    parser.add_argument("--confirmed-timeout-sec", type=int, default=300)
    parser.add_argument("--use-native-uplink-profile", action="store_true")
    parser.add_argument("--tunnel-url-wait-sec", type=int, default=60)
    parser.add_argument("--public-curl-timeout-sec", type=float, default=25.0)
    parser.add_argument("--public-smoke-attempts", type=int, default=6)
    parser.add_argument("--public-smoke-retry-delay-sec", type=float, default=2.5)
    parser.add_argument("--allow-orchestrated-live", action="store_true")
    parser.add_argument("--allow-native-reboot", action="store_true")
    parser.add_argument("--allow-public-live", action="store_true")
    parser.add_argument("--ack-credentialed-wifi", action="store_true")
    parser.add_argument("--ack-public-exposure", action="store_true")
    parser.add_argument("--ack-packet-filter-mutation", action="store_true")
    parser.add_argument("--force-packet-filter-restore-proof", action="store_true")
    parser.add_argument("--enable-cloudflared-egress-allowlist", action="store_true")
    parser.add_argument("--force-cloudflared-egress-allowlist-proof", action="store_true")
    parser.add_argument("--cloudflared-egress-dns4", action="append", default=[])
    parser.add_argument("--cloudflared-egress-tls4", action="append", default=[])
    parser.add_argument("--native-confirm-token", default="")
    parser.add_argument("--public-confirm-token", default="")
    parser.add_argument("--autoconnect-profile", default="")
    parser.add_argument("--no-sync-time", dest="sync_time", action="store_false", default=True)
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta43-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main())
