#!/usr/bin/env python3
"""WSTA55 short-lived persistent public proof runner.

Default execution is host-only preflight.  Live public exposure is available only
with an explicit WSTA55 live gate, then this runner delegates to the existing
WSTA45/WSTA43/WSTA42 path and requires WSTA48 redaction plus TTL-expiry cleanup
proof before returning a live pass.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from argparse import Namespace
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_wsta45_appliance_operator as wsta45  # noqa: E402
import run_wsta48_redacted_result_aggregate as wsta48  # noqa: E402
import run_wsta54_private_lease_artifact as wsta54  # noqa: E402


REPO_ROOT = wsta54.REPO_ROOT
PRIVATE_ROOT = wsta54.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta54.DEFAULT_RUN_BASE
PREFLIGHT_DECISION = "wsta55-short-lived-public-proof-preflight-pass"
PASS_DECISION = "wsta55-short-lived-public-proof-live-pass"
SHORT_LEASE_MAX_TTL_SEC = 300
FORBIDDEN_TEXT_PATTERNS = (
    "trycloudflare.com",
    "public-url.txt",
    "ssid=",
    "psk=",
    "http://",
    "https://",
)


def rel(path: Path) -> str:
    return wsta54.rel(path)


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_stamp(value: _dt.datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def parse_utc_stamp(value: Any) -> _dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return _dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def write_json(path: Path, payload: Any) -> None:
    wsta54.write_json(path, payload)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta54.is_under(path, root)


def load_json(path: Path) -> dict[str, Any]:
    return wsta54.load_json(path)


def redaction_findings(payload: Any) -> list[str]:
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    lowered = text.lower()
    findings = [f"forbidden-text:{item}" for item in FORBIDDEN_TEXT_PATTERNS if item in lowered]
    findings.extend(wsta48.redaction_findings(payload))
    return sorted(set(findings))


def template() -> dict[str, Any]:
    command = [
        "python3",
        rel(Path(__file__).resolve()),
        "--lease-artifact-json",
        "workspace/private/runs/server-distro/<wsta54-run>/wsta54_private_lease.json",
        "--execute-live-short-lease",
        "--allow-operator-live",
        "--allow-native-reboot",
        "--allow-public-live",
        "--ack-credentialed-wifi",
        "--ack-public-exposure",
        "--force-ttl-expiry-proof",
        "--native-confirm-token",
        "<native-confirm-token>",
        "--public-confirm-token",
        "<public-confirm-token>",
    ]
    return {
        "scope": "WSTA55 short-lived persistent public proof",
        "default_mode": "host-only-preflight",
        "short_lease_max_ttl_sec": SHORT_LEASE_MAX_TTL_SEC,
        "command": command,
        "live_action_requires_execute_flag": True,
        "secret_values_logged": 0,
        "public_url_value_logged": False,
    }


def live_safety_flags(args: argparse.Namespace, gate_ok: bool = False) -> dict[str, Any]:
    live_requested = bool(getattr(args, "execute_live_short_lease", False))
    return {
        "device_action": live_requested and gate_ok,
        "boot_flash": False,
        "native_reboot": live_requested and gate_ok and bool(args.allow_native_reboot),
        "wifi_connect": "wsta45-explicit-live-gated" if live_requested else False,
        "dhcp": "wsta45-native-uplink-gated" if live_requested else False,
        "public_tunnel": "wsta45-explicit-public-live-gated" if live_requested else False,
        "public_smoke": "wsta45-explicit-public-live-gated" if live_requested else False,
        "userdata_touch": False,
        "switch_root": False,
        "native_confirm_token_value_logged": False,
        "public_confirm_token_value_logged": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_artifact(path: Path, now: _dt.datetime) -> tuple[bool, str, dict[str, Any]]:
    if not is_under(path, PRIVATE_ROOT):
        return False, "wsta55-blocked-nonprivate-lease-artifact", {"path": rel(path)}
    try:
        artifact = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta55-blocked-lease-artifact-unreadable", {"error": str(exc)}
    findings = redaction_findings(wsta54.redacted_marker(artifact) if artifact.get("schema") == wsta54.PRIVATE_LEASE_SCHEMA else artifact)
    if findings:
        return False, "wsta55-blocked-lease-redaction-finding", {"findings": findings}
    if artifact.get("schema") != wsta54.PRIVATE_LEASE_SCHEMA:
        return False, "wsta55-blocked-lease-schema", {"schema": artifact.get("schema")}
    if artifact.get("mode") != wsta54.wsta53.LEASE_MODE:
        return False, "wsta55-blocked-lease-mode", {"mode": artifact.get("mode")}
    if artifact.get("state") != "ARMED_PRIVATE_LEASE":
        return False, "wsta55-blocked-lease-state", {"state": artifact.get("state")}
    if artifact.get("wsta55_explicit_live_gate_required") is not True:
        return False, "wsta55-blocked-explicit-live-marker-missing", {}
    if artifact.get("wsta54_live_allowed") is not False:
        return False, "wsta55-blocked-wsta54-must-not-authorize-live", {}
    if artifact.get("public_url_value_logged") is not False:
        return False, "wsta55-blocked-public-url-logged", {}
    if artifact.get("secret_values_logged") not in (0, "0", None):
        return False, "wsta55-blocked-secret-values-logged", {}
    if artifact.get("public_url_storage") != "workspace/private-only":
        return False, "wsta55-blocked-public-url-private-storage-required", {}
    if artifact.get("confirm_token_sources") != {"native": "private", "public": "private"}:
        return False, "wsta55-blocked-confirm-token-private-source-required", {}
    try:
        ttl_sec = int(artifact.get("ttl_sec"))
    except (TypeError, ValueError):
        return False, "wsta55-blocked-lease-ttl-invalid", {"ttl_sec": artifact.get("ttl_sec")}
    if ttl_sec <= 0 or ttl_sec > SHORT_LEASE_MAX_TTL_SEC:
        return False, "wsta55-blocked-lease-ttl-not-short", {
            "ttl_sec": ttl_sec,
            "short_lease_max_ttl_sec": SHORT_LEASE_MAX_TTL_SEC,
        }
    issued = parse_utc_stamp(artifact.get("issued_utc"))
    expires = parse_utc_stamp(artifact.get("expires_utc"))
    if issued is None or expires is None or expires <= issued:
        return False, "wsta55-blocked-lease-time-invalid", {
            "issued_utc": artifact.get("issued_utc"),
            "expires_utc": artifact.get("expires_utc"),
        }
    if now >= expires:
        return False, "wsta55-blocked-lease-already-expired", {"expires_utc": artifact.get("expires_utc")}
    return True, "ok", {
        "artifact": artifact,
        "ttl_sec": ttl_sec,
        "issued_utc": artifact.get("issued_utc"),
        "expires_utc": artifact.get("expires_utc"),
        "lease_id_present": bool(artifact.get("lease_id")),
        "lease_id_value_redacted": True,
    }


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.execute_live_short_lease:
        return False, "wsta55-blocked-execute-live-short-lease-required"
    if not args.allow_operator_live:
        return False, "wsta55-blocked-operator-live-allow-required"
    if not args.allow_native_reboot:
        return False, "wsta55-blocked-native-reboot-allow-required"
    if not args.allow_public_live:
        return False, "wsta55-blocked-public-live-allow-required"
    if not args.ack_credentialed_wifi:
        return False, "wsta55-blocked-credentialed-wifi-ack-required"
    if not args.ack_public_exposure:
        return False, "wsta55-blocked-public-exposure-ack-required"
    if not args.force_ttl_expiry_proof:
        return False, "wsta55-blocked-ttl-expiry-proof-required"
    if args.native_confirm_token != wsta45.wsta25.NATIVE_CONFIRM_TOKEN:
        return False, "wsta55-blocked-native-confirm-token-required"
    if args.public_confirm_token != wsta45.PUBLIC_CONFIRM_TOKEN:
        return False, "wsta55-blocked-public-confirm-token-required"
    return True, "ok"


def wsta45_args(args: argparse.Namespace, run_dir: Path) -> argparse.Namespace:
    return wsta45.build_arg_parser().parse_args([
        "--mode",
        "publish",
        "--run-dir",
        str(run_dir / "wsta45-short-lived-publish"),
        "--use-native-uplink-profile",
        "--allow-operator-live",
        "--allow-native-reboot",
        "--allow-public-live",
        "--ack-credentialed-wifi",
        "--ack-public-exposure",
        "--native-confirm-token",
        args.native_confirm_token,
        "--public-confirm-token",
        args.public_confirm_token,
        "--",
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--timeout",
        str(args.timeout),
    ])


def transport_args(args: argparse.Namespace) -> Namespace:
    return Namespace(
        bridge_host=args.bridge_host,
        bridge_port=args.bridge_port,
        timeout=args.timeout,
    )


def cmdv1_summary(record: dict[str, Any]) -> dict[str, Any]:
    text = str(record.get("text", ""))
    kv = wsta45.wsta43.wsta42.wsta24.parse_kv(text)
    return {
        "transport_ok": bool(record.get("transport_ok", True)),
        "rc": record.get("rc"),
        "status": record.get("status"),
        "decision": kv.get("decision"),
        "secret_values_logged": kv.get("secret_values_logged"),
        "autoconnect_decision": kv.get("autoconnect.decision"),
        "supplicant_process_count": kv.get("supplicant.process_count"),
        "wlan0_present": kv.get("wlan0_present"),
    }


def pre_live_cleanup(args: argparse.Namespace) -> dict[str, Any]:
    native = transport_args(args)
    steps: dict[str, dict[str, Any]] = {}
    for name, command in (
        ("hide", ["hide"]),
        ("autoconnect_disable", ["wifi", "autoconnect", "disable"]),
        ("wifi_cleanup", ["wifi", "cleanup"]),
        ("wifi_status", ["wifi", "status"]),
    ):
        record = wsta45.wsta43.wsta42.wsta19.try_cmdv1_retry(
            native,
            command,
            timeout=args.timeout,
            attempts=2,
        )
        steps[name] = cmdv1_summary(record)
    ok = (
        steps["hide"].get("status") == "ok"
        and steps["autoconnect_disable"].get("decision") == "wifi-autoconnect-disabled"
        and steps["wifi_cleanup"].get("decision") == "wifi-cleanup-done"
        and steps["wifi_status"].get("autoconnect_decision") == "wifi-autoconnect-disabled"
        and steps["wifi_status"].get("secret_values_logged") == "0"
    )
    return {
        "ok": ok,
        "steps": steps,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def nested_wsta42(wsta45_result: dict[str, Any]) -> dict[str, Any]:
    return dict(wsta45_result.get("wsta43", {}).get("wsta42", {}) or {})


def live_checks(wsta45_result: dict[str, Any], aggregate: dict[str, Any], ttl_expiry: dict[str, Any]) -> dict[str, Any]:
    wsta42_result = nested_wsta42(wsta45_result)
    checks = dict(wsta42_result.get("checks") or {})
    return {
        "wsta45_pass": wsta45_result.get("decision") == wsta45.PASS_DECISION,
        "wsta48_redaction_ok": bool(aggregate.get("redaction_guard", {}).get("ok")),
        "wsta48_all_pass": bool(aggregate.get("all_pass")),
        "public_smoke_ok": bool(checks.get("public_smoke_ok")),
        "dpublic_cleanup_ok": bool(checks.get("dpublic_cleanup_ok")),
        "packet_filter_restore_ok": bool(checks.get("packet_filter_restore_ok")),
        "native_uplink_profile_cleanup_ok": bool(checks.get("native_uplink_profile_cleanup_ok")),
        "chroot_cleanup_ok": bool(checks.get("chroot_cleanup_ok")),
        "final_selftest_fail_zero": bool(checks.get("final_selftest_fail_zero")),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
        "ttl_expiry_stops_public": bool(ttl_expiry.get("ttl_expiry_stops_public")),
    }


def classify_live(checks: dict[str, Any]) -> str:
    if not checks.get("wsta45_pass"):
        return "wsta55-blocked-wsta45-publish"
    if not checks.get("public_smoke_ok"):
        return "wsta55-blocked-public-smoke"
    if not checks.get("dpublic_cleanup_ok"):
        return "wsta55-blocked-dpublic-cleanup"
    if not checks.get("packet_filter_restore_ok"):
        return "wsta55-blocked-packet-filter-restore"
    if not checks.get("native_uplink_profile_cleanup_ok"):
        return "wsta55-blocked-native-uplink-profile-cleanup"
    if not checks.get("chroot_cleanup_ok"):
        return "wsta55-blocked-chroot-cleanup"
    if not checks.get("final_selftest_fail_zero"):
        return "wsta55-blocked-final-selftest"
    if not checks.get("wsta48_redaction_ok") or not checks.get("wsta48_all_pass"):
        return "wsta55-blocked-wsta48-redaction"
    if not checks.get("ttl_expiry_stops_public"):
        return "wsta55-blocked-ttl-expiry"
    return PASS_DECISION


def ttl_expiry_proof(lease: dict[str, Any], args: argparse.Namespace, cleanup_ok: bool) -> dict[str, Any]:
    return {
        "forced_for_wsta55": bool(args.force_ttl_expiry_proof),
        "lease_id_present": bool(lease.get("lease_id")),
        "lease_id_value_redacted": True,
        "ttl_sec": lease.get("ttl_sec"),
        "public_state_after_expiry": "PUBLIC_OFF" if cleanup_ok else "INCIDENT_STOP",
        "ttl_expiry_stops_public": bool(args.force_ttl_expiry_proof and cleanup_ok),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "lease": result.get("lease_redacted", {}),
        "checks": result.get("checks", {}),
        "ttl_expiry": result.get("ttl_expiry", {}),
        "wsta45": wsta45.public_summary(result.get("wsta45", {})) if result.get("wsta45") else None,
        "wsta48": result.get("wsta48_redacted", {}),
        "safety": result.get("safety", {}),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta55-short-lived-public-proof-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA55 short-lived persistent public proof",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta55-blocked",
        "gate_decision": "not-run",
        "safety": live_safety_flags(args),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta55-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta55_result.json"
    if args.lease_artifact_json is None:
        result["decision"] = "wsta55-blocked-lease-artifact-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    artifact_path = resolve_path(args.lease_artifact_json)
    artifact_ok, artifact_decision, artifact_detail = validate_artifact(artifact_path, started)
    result["gate_decision"] = artifact_decision
    result["lease_redacted"] = {
        "source": rel(artifact_path),
        "ttl_sec": artifact_detail.get("ttl_sec"),
        "issued_utc": artifact_detail.get("issued_utc"),
        "expires_utc": artifact_detail.get("expires_utc"),
        "lease_id_present": bool(artifact_detail.get("lease_id_present")),
        "lease_id_value_redacted": True,
        "short_lease_max_ttl_sec": SHORT_LEASE_MAX_TTL_SEC,
    }
    if not artifact_ok:
        result["decision"] = artifact_decision
        result["gate_detail"] = artifact_detail
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    if not args.execute_live_short_lease:
        result["decision"] = PREFLIGHT_DECISION
        result["checks"] = {
            "lease_artifact_ok": True,
            "short_lease_ttl_ok": True,
            "live_execution_requested": False,
            "wsta55_live_ready": True,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    gate_ok, gate_decision = explicit_live_gate(args)
    result["gate_decision"] = gate_decision
    result["safety"] = live_safety_flags(args, gate_ok)
    if not gate_ok:
        result["decision"] = gate_decision
        result["checks"] = {
            "lease_artifact_ok": True,
            "live_execution_requested": True,
            "explicit_live_gate": False,
        }
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    cleanup = pre_live_cleanup(args)
    result["pre_live_cleanup"] = cleanup
    result["checks"] = {
        "lease_artifact_ok": True,
        "live_execution_requested": True,
        "explicit_live_gate": True,
        "pre_live_cleanup_ok": bool(cleanup.get("ok")),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    write_json(out_path, result)
    if not cleanup.get("ok"):
        result["decision"] = "wsta55-blocked-pre-live-cleanup"
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    nested = wsta45.run(wsta45_args(args, run_dir))
    result["wsta45"] = nested
    write_json(out_path, result)

    aggregate = wsta48.build_aggregate([run_dir / "wsta45-short-lived-publish"])
    aggregate_path = run_dir / "wsta48_result.json"
    write_json(aggregate_path, aggregate)
    wsta42_result = nested_wsta42(nested)
    cleanup_ok = bool(
        wsta42_result.get("checks", {}).get("dpublic_cleanup_ok")
        and wsta42_result.get("checks", {}).get("packet_filter_restore_ok")
        and wsta42_result.get("checks", {}).get("native_uplink_profile_cleanup_ok")
        and wsta42_result.get("checks", {}).get("chroot_cleanup_ok")
    )
    result["ttl_expiry"] = ttl_expiry_proof(artifact_detail["artifact"], args, cleanup_ok)
    result["wsta48_redacted"] = {
        "path": rel(aggregate_path),
        "all_pass": bool(aggregate.get("all_pass")),
        "redaction_guard_ok": bool(aggregate.get("redaction_guard", {}).get("ok")),
        "result_count": aggregate.get("result_count"),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    result["checks"] = live_checks(nested, aggregate, result["ttl_expiry"])
    result["decision"] = classify_live(result["checks"])
    findings = redaction_findings(public_summary(result))
    if findings:
        result["decision"] = "wsta55-blocked-public-summary-redaction-finding"
        result["gate_detail"] = {"findings": findings}
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--lease-artifact-json", type=Path)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--execute-live-short-lease", action="store_true")
    parser.add_argument("--allow-operator-live", action="store_true")
    parser.add_argument("--allow-native-reboot", action="store_true")
    parser.add_argument("--allow-public-live", action="store_true")
    parser.add_argument("--ack-credentialed-wifi", action="store_true")
    parser.add_argument("--ack-public-exposure", action="store_true")
    parser.add_argument("--force-ttl-expiry-proof", action="store_true")
    parser.add_argument("--native-confirm-token", default="")
    parser.add_argument("--public-confirm-token", default="")
    parser.add_argument("--print-template", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.print_template:
        print(json.dumps(template(), indent=2, sort_keys=True))
        return 0
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta55-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") in {PREFLIGHT_DECISION, PASS_DECISION} else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
