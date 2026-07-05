#!/usr/bin/env python3
"""WSTA58 renewal and manual-stop proof runner.

Default execution is host-only preflight.  Live renewal proof is available only
with an explicit WSTA58 gate, then this runner performs two independent WSTA55
short-lease live proofs and requires a final public-off/manual-stop cleanup plus
WSTA48 redaction before returning a pass.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_wsta48_redacted_result_aggregate as wsta48  # noqa: E402
import run_wsta54_private_lease_artifact as wsta54  # noqa: E402
import run_wsta55_short_lived_public_proof as wsta55  # noqa: E402


REPO_ROOT = wsta55.REPO_ROOT
PRIVATE_ROOT = wsta55.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta55.DEFAULT_RUN_BASE
PREFLIGHT_DECISION = "wsta58-renewal-manual-stop-preflight-pass"
PASS_DECISION = "wsta58-renewal-manual-stop-live-pass"


def rel(path: Path) -> str:
    return wsta55.rel(path)


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_stamp(value: _dt.datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    wsta55.write_json(path, payload)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta55.is_under(path, root)


def live_safety_flags(args: argparse.Namespace, gate_ok: bool = False) -> dict[str, Any]:
    live_requested = bool(getattr(args, "execute_renewal_manual_stop", False))
    return {
        "device_action": live_requested and gate_ok,
        "boot_flash": False,
        "native_reboot": live_requested and gate_ok and bool(args.allow_native_reboot),
        "wifi_connect": "wsta55-explicit-live-gated" if live_requested else False,
        "dhcp": "wsta55-native-uplink-gated" if live_requested else False,
        "public_tunnel": "wsta55-explicit-public-live-gated" if live_requested else False,
        "public_smoke": "wsta55-explicit-public-live-gated" if live_requested else False,
        "userdata_touch": False,
        "switch_root": False,
        "native_confirm_token_value_logged": False,
        "public_confirm_token_value_logged": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    command = [
        "python3",
        rel(Path(__file__).resolve()),
        "--initial-lease-artifact-json",
        "workspace/private/runs/server-distro/<wsta54-initial>/wsta54_private_lease.json",
        "--renewal-wsta53-result-json",
        "workspace/private/runs/server-distro/<wsta53-renewal>/wsta53_result.json",
        "--execute-renewal-manual-stop",
        "--allow-operator-live",
        "--allow-native-reboot",
        "--allow-public-live",
        "--ack-credentialed-wifi",
        "--ack-public-exposure",
        "--ack-packet-filter-mutation",
        "--force-packet-filter-restore-proof",
        "--force-ttl-expiry-proof",
        "--force-manual-stop-proof",
        "--native-confirm-token",
        "<native-confirm-token>",
        "--public-confirm-token",
        "<public-confirm-token>",
    ]
    return {
        "scope": "WSTA58 renewal and manual-stop proof",
        "default_mode": "host-only-preflight",
        "requires_initial_private_short_lease": True,
        "renewal_private_short_lease_minted_after_initial": True,
        "command": command,
        "live_action_requires_execute_flag": True,
        "secret_values_logged": 0,
        "public_url_value_logged": False,
    }


def validate_pair(args: argparse.Namespace, now: _dt.datetime) -> tuple[bool, str, dict[str, Any]]:
    if args.initial_lease_artifact_json is None:
        return False, "wsta58-blocked-initial-lease-artifact-required", {}
    initial_path = resolve_path(args.initial_lease_artifact_json)
    renewal_path = resolve_path(args.renewal_lease_artifact_json) if args.renewal_lease_artifact_json else None
    renewal_source_path = resolve_path(args.renewal_wsta53_result_json) if args.renewal_wsta53_result_json else None
    if renewal_path is None and renewal_source_path is None:
        return False, "wsta58-blocked-renewal-lease-or-source-required", {}
    if not is_under(initial_path, PRIVATE_ROOT):
        return False, "wsta58-blocked-nonprivate-lease-artifact", {"initial_path": rel(initial_path)}
    if renewal_path is not None and not is_under(renewal_path, PRIVATE_ROOT):
        return False, "wsta58-blocked-nonprivate-lease-artifact", {"renewal_path": rel(renewal_path)}
    if renewal_source_path is not None and not is_under(renewal_source_path, PRIVATE_ROOT):
        return False, "wsta58-blocked-nonprivate-renewal-source", {"renewal_source": rel(renewal_source_path)}
    initial_ok, initial_decision, initial_detail = wsta55.validate_artifact(initial_path, now)
    detail = {
        "initial": redacted_lease_detail(initial_path, initial_detail),
        "renewal": {},
        "renewal_refresh_source": {},
        "distinct_lease_ids": False,
        "renewal_lease_refresh_ready": False,
    }
    if not initial_ok:
        return False, f"wsta58-blocked-initial-{initial_decision}", detail
    initial_artifact = initial_detail.get("artifact") or {}
    detail["initial"]["lease_id_present"] = bool(initial_artifact.get("lease_id"))
    detail["initial_artifact"] = initial_artifact

    if renewal_path is not None:
        renewal_ok, renewal_decision, renewal_detail = wsta55.validate_artifact(renewal_path, now)
        detail["renewal"] = redacted_lease_detail(renewal_path, renewal_detail)
        if not renewal_ok:
            return False, f"wsta58-blocked-renewal-{renewal_decision}", detail
        renewal_artifact = renewal_detail.get("artifact") or {}
        if initial_artifact.get("lease_id") == renewal_artifact.get("lease_id"):
            return False, "wsta58-blocked-renewal-lease-not-distinct", detail
        detail["distinct_lease_ids"] = True
        detail["renewal"]["lease_id_present"] = bool(renewal_artifact.get("lease_id"))
        detail["renewal_artifact"] = renewal_artifact
    if renewal_source_path is not None:
        source_ok, source_decision, source_detail = validate_renewal_source(renewal_source_path)
        detail["renewal_refresh_source"] = redacted_renewal_source_detail(renewal_source_path, source_detail)
        if not source_ok:
            return False, source_decision, detail
        detail["renewal_lease_refresh_ready"] = True
        detail["renewal_source_path"] = renewal_source_path
    return True, "ok", detail


def validate_renewal_source(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = wsta54.load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta58-blocked-renewal-source-unreadable", {"error": str(exc)}
    ok, decision, detail = wsta54.validate_wsta53_result(payload)
    if not ok:
        return False, f"wsta58-blocked-renewal-source-{decision}", detail
    ttl_sec = int(detail.get("ttl_sec", 0))
    if ttl_sec <= 0 or ttl_sec > wsta55.SHORT_LEASE_MAX_TTL_SEC:
        return False, "wsta58-blocked-renewal-source-ttl-not-short", {
            "ttl_sec": ttl_sec,
            "short_lease_max_ttl_sec": wsta55.SHORT_LEASE_MAX_TTL_SEC,
        }
    return True, "ok", {
        "ttl_sec": ttl_sec,
        "renewal_source_decision": payload.get("decision"),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def redacted_renewal_source_detail(path: Path, detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": rel(path),
        "ttl_sec": detail.get("ttl_sec"),
        "lease_minted_after_initial": True,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def redacted_lease_detail(path: Path, detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": rel(path),
        "ttl_sec": detail.get("ttl_sec"),
        "issued_utc": detail.get("issued_utc"),
        "expires_utc": detail.get("expires_utc"),
        "lease_id_present": bool(detail.get("lease_id_present")),
        "lease_id_value_redacted": True,
        "short_lease_max_ttl_sec": wsta55.SHORT_LEASE_MAX_TTL_SEC,
    }


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.execute_renewal_manual_stop:
        return False, "wsta58-blocked-execute-renewal-manual-stop-required"
    if not args.allow_operator_live:
        return False, "wsta58-blocked-operator-live-allow-required"
    if not args.allow_native_reboot:
        return False, "wsta58-blocked-native-reboot-allow-required"
    if not args.allow_public_live:
        return False, "wsta58-blocked-public-live-allow-required"
    if not args.ack_credentialed_wifi:
        return False, "wsta58-blocked-credentialed-wifi-ack-required"
    if not args.ack_public_exposure:
        return False, "wsta58-blocked-public-exposure-ack-required"
    if not args.ack_packet_filter_mutation:
        return False, "wsta58-blocked-packet-filter-mutation-ack-required"
    if not args.force_packet_filter_restore_proof:
        return False, "wsta58-blocked-packet-filter-restore-proof-required"
    if not args.force_ttl_expiry_proof:
        return False, "wsta58-blocked-ttl-expiry-proof-required"
    if not args.force_manual_stop_proof:
        return False, "wsta58-blocked-manual-stop-proof-required"
    if args.native_confirm_token != wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN:
        return False, "wsta58-blocked-native-confirm-token-required"
    if args.public_confirm_token != wsta55.wsta45.PUBLIC_CONFIRM_TOKEN:
        return False, "wsta58-blocked-public-confirm-token-required"
    return True, "ok"


def wsta55_args(args: argparse.Namespace, run_dir: Path, lease_path: Path, label: str) -> argparse.Namespace:
    return wsta55.build_arg_parser().parse_args([
        "--run-dir",
        str(run_dir / f"{label}-wsta55"),
        "--lease-artifact-json",
        str(lease_path),
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--timeout",
        str(args.timeout),
        "--local-image",
        str(args.local_image),
        "--local-image-sha256",
        args.local_image_sha256,
        "--remote-image",
        args.remote_image,
        "--remote-clean-image",
        args.remote_clean_image,
        "--execute-live-short-lease",
        "--allow-operator-live",
        "--allow-native-reboot",
        "--allow-public-live",
        "--ack-credentialed-wifi",
        "--ack-public-exposure",
        "--ack-packet-filter-mutation",
        "--force-packet-filter-restore-proof",
        "--force-ttl-expiry-proof",
        "--native-confirm-token",
        args.native_confirm_token,
        "--public-confirm-token",
        args.public_confirm_token,
    ])


def mint_renewal_lease(args: argparse.Namespace, run_dir: Path) -> tuple[bool, dict[str, Any], Path | None]:
    source_path = resolve_path(args.renewal_wsta53_result_json)
    wsta54_args = wsta54.build_arg_parser().parse_args([
        "--run-dir",
        str(run_dir / "renewal-wsta54-live-refresh"),
        "--wsta53-result-json",
        str(source_path),
    ])
    result = wsta54.run(wsta54_args)
    if result.get("decision") != wsta54.PASS_DECISION:
        return False, result, None
    artifact_path = REPO_ROOT / str(result["private_lease_artifact"])
    return True, result, artifact_path


def manual_stop_cleanup(args: argparse.Namespace) -> dict[str, Any]:
    cleanup = wsta55.pre_live_cleanup(args)
    return {
        **cleanup,
        "manual_stop_requested": True,
        "manual_stop_public_state": "PUBLIC_OFF" if cleanup.get("ok") else "INCIDENT_STOP",
    }


def live_checks(initial: dict[str, Any],
                renewal: dict[str, Any],
                aggregate: dict[str, Any],
                stop_cleanup: dict[str, Any]) -> dict[str, Any]:
    return {
        "initial_wsta55_pass": initial.get("decision") == wsta55.PASS_DECISION,
        "renewal_wsta55_pass": renewal.get("decision") == wsta55.PASS_DECISION,
        "initial_packet_filter_restore_ok": bool(initial.get("checks", {}).get("packet_filter_restore_ok")),
        "renewal_packet_filter_restore_ok": bool(renewal.get("checks", {}).get("packet_filter_restore_ok")),
        "renewal_requires_second_gate": True,
        "manual_stop_cleanup_ok": bool(stop_cleanup.get("ok")),
        "manual_stop_public_state_off": stop_cleanup.get("manual_stop_public_state") == "PUBLIC_OFF",
        "wsta48_redaction_ok": bool(aggregate.get("redaction_guard", {}).get("ok")),
        "wsta48_all_pass": bool(aggregate.get("all_pass")),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def classify_live(checks: dict[str, Any]) -> str:
    if not checks.get("initial_wsta55_pass"):
        return "wsta58-blocked-initial-wsta55"
    if not checks.get("renewal_wsta55_pass"):
        return "wsta58-blocked-renewal-wsta55"
    if not checks.get("initial_packet_filter_restore_ok") or not checks.get("renewal_packet_filter_restore_ok"):
        return "wsta58-blocked-packet-filter-restore"
    if not checks.get("manual_stop_cleanup_ok") or not checks.get("manual_stop_public_state_off"):
        return "wsta58-blocked-manual-stop-cleanup"
    if not checks.get("wsta48_redaction_ok") or not checks.get("wsta48_all_pass"):
        return "wsta58-blocked-wsta48-redaction"
    return PASS_DECISION


def redaction_findings(payload: Any) -> list[str]:
    return wsta55.redaction_findings(payload)


def wsta55_public(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "gate_decision": result.get("gate_decision"),
        "checks": result.get("checks", {}),
        "ttl_expiry": result.get("ttl_expiry", {}),
        "image_prep": wsta55.image_prep_public(result),
        "wsta48": result.get("wsta48_redacted", {}),
        "safety": result.get("safety", {}),
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "lease_pair_redacted": result.get("lease_pair_redacted", {}),
        "checks": result.get("checks", {}),
        "initial": wsta55_public(result.get("initial_wsta55", {})) if result.get("initial_wsta55") else None,
        "renewal": wsta55_public(result.get("renewal_wsta55", {})) if result.get("renewal_wsta55") else None,
        "renewal_lease_refresh": result.get("renewal_lease_refresh_redacted", {}),
        "manual_stop": result.get("manual_stop", {}),
        "wsta48": result.get("wsta48_redacted", {}),
        "safety": result.get("safety", {}),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta58-renewal-manual-stop-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA58 renewal and manual-stop proof",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta58-blocked",
        "gate_decision": "not-run",
        "safety": live_safety_flags(args),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta58-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta58_result.json"

    pair_ok, pair_decision, pair_detail = validate_pair(args, started)
    result["gate_decision"] = pair_decision
    result["lease_pair_redacted"] = {
        "initial": pair_detail.get("initial", {}),
        "renewal": pair_detail.get("renewal", {}),
        "renewal_refresh_source": pair_detail.get("renewal_refresh_source", {}),
        "distinct_lease_ids": bool(pair_detail.get("distinct_lease_ids")),
        "renewal_lease_refresh_ready": bool(pair_detail.get("renewal_lease_refresh_ready")),
    }
    if not pair_ok:
        result["decision"] = pair_decision
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    if not args.execute_renewal_manual_stop:
        result["decision"] = PREFLIGHT_DECISION
        result["checks"] = {
            "initial_lease_artifact_ok": True,
            "renewal_lease_artifact_ok": bool(pair_detail.get("renewal_artifact")),
            "renewal_lease_refresh_ready": bool(pair_detail.get("renewal_lease_refresh_ready")),
            "distinct_lease_ids": bool(pair_detail.get("distinct_lease_ids")),
            "distinct_lease_ids_deferred_to_live_refresh": bool(pair_detail.get("renewal_lease_refresh_ready")),
            "live_execution_requested": False,
            "wsta58_live_ready": True,
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
            "initial_lease_artifact_ok": True,
            "renewal_lease_artifact_ok": bool(pair_detail.get("renewal_artifact")),
            "renewal_lease_refresh_ready": bool(pair_detail.get("renewal_lease_refresh_ready")),
            "distinct_lease_ids": bool(pair_detail.get("distinct_lease_ids")),
            "live_execution_requested": True,
            "explicit_live_gate": False,
        }
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    initial_path = resolve_path(args.initial_lease_artifact_json)
    initial = wsta55.run(wsta55_args(args, run_dir, initial_path, "initial"))
    result["initial_wsta55"] = initial
    write_json(out_path, result)
    if initial.get("decision") != wsta55.PASS_DECISION:
        result["renewal_wsta55"] = {"decision": "wsta58-skipped-renewal-after-initial-failure"}
        result["manual_stop"] = manual_stop_cleanup(args)
        result["wsta48_redacted"] = {
            "all_pass": False,
            "redaction_guard_ok": True,
            "result_count": 1,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        result["checks"] = live_checks(
            initial,
            result["renewal_wsta55"],
            {"redaction_guard": {"ok": True}, "all_pass": False},
            result["manual_stop"],
        )
        result["decision"] = classify_live(result["checks"])
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    if args.renewal_wsta53_result_json:
        refresh_ok, refresh_result, minted_path = mint_renewal_lease(args, run_dir)
        result["renewal_lease_refresh_redacted"] = {
            "decision": refresh_result.get("decision"),
            "private_lease_artifact_present": bool(refresh_result.get("private_lease_artifact")),
            "lease_id_value_redacted": True,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        write_json(out_path, result)
        if not refresh_ok or minted_path is None:
            result["renewal_wsta55"] = {"decision": "wsta58-blocked-renewal-lease-refresh"}
            result["manual_stop"] = manual_stop_cleanup(args)
            result["checks"] = live_checks(
                initial,
                result["renewal_wsta55"],
                {"redaction_guard": {"ok": True}},
                result["manual_stop"],
            )
            result["decision"] = "wsta58-blocked-renewal-lease-refresh"
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result
        renewal_path = minted_path
        renewal_artifact = wsta54.load_json(renewal_path)
        result["lease_pair_redacted"]["renewal"] = redacted_lease_detail(
            renewal_path,
            {
                "ttl_sec": renewal_artifact.get("ttl_sec"),
                "issued_utc": renewal_artifact.get("issued_utc"),
                "expires_utc": renewal_artifact.get("expires_utc"),
                "lease_id_present": bool(renewal_artifact.get("lease_id")),
            },
        )
        result["lease_pair_redacted"]["distinct_lease_ids"] = (
            pair_detail["initial_artifact"].get("lease_id") != renewal_artifact.get("lease_id")
        )
        write_json(out_path, result)
    else:
        renewal_path = resolve_path(args.renewal_lease_artifact_json)
    renewal = wsta55.run(wsta55_args(args, run_dir, renewal_path, "renewal"))
    result["renewal_wsta55"] = renewal
    write_json(out_path, result)

    stop_cleanup = manual_stop_cleanup(args)
    result["manual_stop"] = stop_cleanup
    aggregate = wsta48.build_aggregate([
        run_dir / "initial-wsta55" / "wsta45-short-lived-publish",
        run_dir / "renewal-wsta55" / "wsta45-short-lived-publish",
    ])
    aggregate_path = run_dir / "wsta48_result.json"
    write_json(aggregate_path, aggregate)
    result["wsta48_redacted"] = {
        "path": rel(aggregate_path),
        "all_pass": bool(aggregate.get("all_pass")),
        "redaction_guard_ok": bool(aggregate.get("redaction_guard", {}).get("ok")),
        "result_count": aggregate.get("result_count"),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    result["checks"] = live_checks(initial, renewal, aggregate, stop_cleanup)
    result["decision"] = classify_live(result["checks"])
    findings = redaction_findings(public_summary(result))
    if findings:
        result["decision"] = "wsta58-blocked-public-summary-redaction-finding"
        result["gate_detail"] = {"findings": findings}
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--initial-lease-artifact-json", type=Path)
    parser.add_argument("--renewal-lease-artifact-json", type=Path)
    parser.add_argument("--renewal-wsta53-result-json", type=Path)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--local-image", type=Path, default=wsta55.wsta45.wsta43.wsta42.DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--local-image-sha256", default=wsta55.wsta45.wsta43.wsta42.DEFAULT_LOCAL_IMAGE_SHA256)
    parser.add_argument("--remote-image", default=wsta55.wsta45.wsta43.wsta42.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--remote-clean-image", default=wsta55.wsta45.wsta43.wsta42.DEFAULT_REMOTE_CLEAN_IMAGE)
    parser.add_argument("--execute-renewal-manual-stop", action="store_true")
    parser.add_argument("--allow-operator-live", action="store_true")
    parser.add_argument("--allow-native-reboot", action="store_true")
    parser.add_argument("--allow-public-live", action="store_true")
    parser.add_argument("--ack-credentialed-wifi", action="store_true")
    parser.add_argument("--ack-public-exposure", action="store_true")
    parser.add_argument("--ack-packet-filter-mutation", action="store_true")
    parser.add_argument("--force-packet-filter-restore-proof", action="store_true")
    parser.add_argument("--force-ttl-expiry-proof", action="store_true")
    parser.add_argument("--force-manual-stop-proof", action="store_true")
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
        payload = {"decision": "wsta58-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") in {PREFLIGHT_DECISION, PASS_DECISION} else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
