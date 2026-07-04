#!/usr/bin/env python3
"""WSTA53 persistent D-public lease parser and redacted plan generator.

This runner is source/host-only.  It does not touch the device, start Wi-Fi,
start a tunnel, reboot native init, flash boot, or perform public smoke.  Its job
is to make the WSTA52 persistent-exposure contract machine-checkable before the
future WSTA54 private lease artifact step.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_RUN_BASE = REPO_ROOT / "workspace" / "private" / "runs" / "server-distro"
PASS_DECISION = "wsta53-persistent-exposure-plan-pass"
DEFAULT_TTL_SEC = 1800
MAX_TTL_SEC = 14400
LEASE_SCHEMA = "a90-wsta-persistent-lease-v1"
LEASE_MODE = "persistent-dpublic-lease"
FORBIDDEN_PUBLIC_FIELDS = {
    "raw_public_url",
    "ssid",
    "psk",
    "bssid",
    "mac",
    "ip",
    "gateway",
    "dns",
    "confirm_token_value",
    "native_confirm_token",
    "public_confirm_token",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def template() -> dict[str, Any]:
    return {
        "schema": LEASE_SCHEMA,
        "mode": LEASE_MODE,
        "ttl_sec": DEFAULT_TTL_SEC,
        "operator_ack_credentialed_wifi": False,
        "operator_ack_public_exposure": False,
        "native_confirm_token_source": "private",
        "public_confirm_token_source": "private",
        "public_url_storage": "workspace/private-only",
        "notes": [
            "Set acknowledgements true only for an operator-approved private run.",
            "Do not add raw public URL, Wi-Fi identifiers, IP data, or token values.",
        ],
    }


def load_lease(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("lease JSON must be an object")
    return payload


def forbidden_fields(payload: dict[str, Any]) -> list[str]:
    found: list[str] = []

    def walk(value: Any, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                lowered = str(key).lower()
                child_prefix = f"{prefix}.{key}" if prefix else str(key)
                if lowered in FORBIDDEN_PUBLIC_FIELDS:
                    found.append(child_prefix)
                walk(child, child_prefix)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{prefix}[{index}]")

    walk(payload)
    return sorted(found)


def merged_request(args: argparse.Namespace) -> dict[str, Any]:
    lease = load_lease(args.lease_json)
    request = template()
    request.update(lease)
    if args.ttl_sec is not None:
        request["ttl_sec"] = args.ttl_sec
    if args.ack_credentialed_wifi:
        request["operator_ack_credentialed_wifi"] = True
    if args.ack_public_exposure:
        request["operator_ack_public_exposure"] = True
    if args.native_confirm_token_source:
        request["native_confirm_token_source"] = args.native_confirm_token_source
    if args.public_confirm_token_source:
        request["public_confirm_token_source"] = args.public_confirm_token_source
    return request


def validate_request(request: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    forbidden = forbidden_fields(request)
    if forbidden:
        return False, "wsta53-blocked-forbidden-field", {"forbidden_fields": forbidden}
    if request.get("schema") != LEASE_SCHEMA:
        return False, "wsta53-blocked-schema", {"schema": request.get("schema")}
    if request.get("mode") != LEASE_MODE:
        return False, "wsta53-blocked-mode", {"mode": request.get("mode")}
    try:
        ttl_sec = int(request.get("ttl_sec"))
    except (TypeError, ValueError):
        return False, "wsta53-blocked-ttl-invalid", {"ttl_sec": request.get("ttl_sec")}
    if ttl_sec <= 0 or ttl_sec > MAX_TTL_SEC:
        return False, "wsta53-blocked-ttl-out-of-range", {
            "ttl_sec": ttl_sec,
            "maximum_lease_ttl_sec": MAX_TTL_SEC,
        }
    if request.get("operator_ack_credentialed_wifi") is not True:
        return False, "wsta53-blocked-credentialed-wifi-ack-required", {}
    if request.get("operator_ack_public_exposure") is not True:
        return False, "wsta53-blocked-public-exposure-ack-required", {}
    if request.get("native_confirm_token_source") != "private":
        return False, "wsta53-blocked-native-confirm-token-private-source-required", {}
    if request.get("public_confirm_token_source") != "private":
        return False, "wsta53-blocked-public-confirm-token-private-source-required", {}
    if request.get("public_url_storage") != "workspace/private-only":
        return False, "wsta53-blocked-public-url-private-storage-required", {}
    return True, "ok", {"ttl_sec": ttl_sec}


def redacted_request(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": request.get("schema"),
        "mode": request.get("mode"),
        "ttl_sec": int(request.get("ttl_sec", 0) or 0),
        "operator_ack_credentialed_wifi": bool(request.get("operator_ack_credentialed_wifi")),
        "operator_ack_public_exposure": bool(request.get("operator_ack_public_exposure")),
        "native_confirm_token_source": request.get("native_confirm_token_source"),
        "public_confirm_token_source": request.get("public_confirm_token_source"),
        "public_url_storage": request.get("public_url_storage"),
    }


def redacted_plan(request: dict[str, Any], gate_ok: bool) -> dict[str, Any]:
    ttl_sec = int(request.get("ttl_sec", 0) or 0)
    return {
        "contract": "wsta52-persistent-exposure-design",
        "default_state": "public-off",
        "lease": {
            "ttl_sec": ttl_sec,
            "maximum_lease_ttl_sec": MAX_TTL_SEC,
            "renewal_requires_host_gate": True,
            "boot_autostart_without_valid_private_lease": False,
        },
        "flow": [
            "WSTA45 operator wrapper",
            "WSTA43 orchestrator",
            "WSTA28 reboot/materialization scan-green precondition",
            "WSTA42 native-owned STA uplink + Debian D-public quick Tunnel",
            "WSTA48 redacted aggregate",
        ],
        "future_live_allowed": False,
        "wsta54_private_artifact_ready": gate_ok,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
        "cleanup_required": [
            "dpublic_cleanup_ok",
            "cloudflared_absent",
            "smoke_service_absent",
            "native_uplink_profile_cleanup_ok",
            "helper_cleanup_ok",
            "chroot_cleanup_ok",
            "wifi_cleanup_ok",
            "post_selftest_fail_zero",
            "wsta48_redaction_guard_ok",
        ],
    }


def classify(gate_ok: bool, gate_decision: str) -> str:
    return PASS_DECISION if gate_ok else gate_decision


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "request": result.get("request_redacted", {}),
        "plan": result.get("plan_redacted", {}),
        "safety": result.get("safety", {}),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta53-persistent-exposure-plan-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta53_result.json"

    request = merged_request(args)
    gate_ok, gate_decision, detail = validate_request(request)
    result: dict[str, Any] = {
        "scope": "WSTA53 persistent exposure lease parser and redacted plan generator",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "gate_decision": gate_decision,
        "decision": classify(gate_ok, gate_decision),
        "request_redacted": redacted_request(request),
        "plan_redacted": redacted_plan(request, gate_ok),
        "gate_detail": detail,
        "safety": {
            "device_action": False,
            "boot_flash": False,
            "native_reboot": False,
            "wifi_connect": False,
            "dhcp": False,
            "public_tunnel": False,
            "public_smoke": False,
            "userdata_touch": False,
            "switch_root": False,
            "native_confirm_token_value_logged": False,
            "public_confirm_token_value_logged": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
        "ended_utc": utc_stamp(),
    }
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--lease-json", type=Path)
    parser.add_argument("--ttl-sec", type=int)
    parser.add_argument("--ack-credentialed-wifi", action="store_true")
    parser.add_argument("--ack-public-exposure", action="store_true")
    parser.add_argument("--native-confirm-token-source", choices=["private", "missing", "public"])
    parser.add_argument("--public-confirm-token-source", choices=["private", "missing", "public"])
    parser.add_argument("--print-template", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.print_template:
        print(json.dumps(template(), indent=2, sort_keys=True))
        return 0
    result = run(args)
    summary = result if args.print_full_json else public_summary(result)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
