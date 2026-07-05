#!/usr/bin/env python3
"""WSTA212 host-only native uplink root-boundary policy.

Consumes existing source/live evidence and emits a deterministic policy for
``wsta-native-uplink-helper``:

  * Debian may use only the redacted native Wi-Fi service client status/scan
    surface;
  * association, DHCP, ping, routing, credentials, and public exposure remain
    native-owned boundary operations;
  * the native uplink helper remains excluded from Debian service seccomp and
    service-launcher enforcement.

This unit is host-only.  It does not touch the device, flash, reboot, connect
Wi-Fi, run DHCP, open a public tunnel, mutate packet filters, write userdata,
switch root, or modify any rootfs.
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

import run_wsta154_seccomp_launcher_gate_model as wsta154  # noqa: E402


REPO_ROOT = wsta154.REPO_ROOT
PRIVATE_ROOT = wsta154.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta154.DEFAULT_RUN_BASE
DEFAULT_WSTA90_MANIFEST = (
    DEFAULT_RUN_BASE
    / "wsta90-service-hardening-manifest-20260704T131000Z"
    / "wsta90_service_hardening_manifest.json"
)
DEFAULT_WSTA22_RESULT = (
    DEFAULT_RUN_BASE
    / "wsta22-native-wifi-service-client-20260704T011641Z"
    / "wsta22_result.json"
)
DEFAULT_WSTA154_MODEL = (
    DEFAULT_RUN_BASE
    / "wsta154-seccomp-launcher-gate-model-20260705T1210KST"
    / "wsta154_seccomp_launcher_gate_model.json"
)
DEFAULT_HELPER_SOURCE = SCRIPT_DIR / "a90_native_wifi_service_client.sh"
PASS_DECISION = "wsta212-native-uplink-boundary-policy-source-pass"
POLICY_SCHEMA = "a90-wsta212-native-uplink-boundary-policy-v1"
POLICY_STATE = "NATIVE_UPLINK_ROOT_BOUNDARY_POLICY_SOURCE_DEFINED"
POLICY_NAME = "wsta212_native_uplink_boundary_policy.json"
SUMMARY_NAME = "wsta212_result.json"
MARKDOWN_NAME = "wsta212_native_uplink_boundary_policy.md"
ALLOWED_DEBIAN_OPS = ["status", "scan"]
DENIED_DEBIAN_OPS = [
    "connect",
    "associate",
    "association",
    "dhcp",
    "ping",
    "public-tunnel",
    "tunnel",
]
RESPONSE_ALLOWLIST_KEYS = [
    "version",
    "seq",
    "op",
    "owner",
    "rc",
    "wlan0_present",
    "wlan0_ifindex",
    "wlan0_flags",
    "supplicant_process_count",
    "dhcp_routing",
    "public_tunnel",
    "credentials",
    "connect",
    "raw_results_redacted",
    "scan_result_count",
    "decision",
]


def rel(path: Path) -> str:
    return wsta154.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta154.is_under(path, root)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def safety_flags() -> dict[str, Any]:
    return {
        "device_action": False,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "wifi_association": False,
        "dhcp": False,
        "ping": False,
        "public_tunnel": False,
        "public_smoke": False,
        "packet_filter_mutation": False,
        "userdata_touch": False,
        "switch_root": False,
        "rootfs_mutation": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "policy": result.get("policy", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def service_by_name(manifest_result: dict[str, Any], name: str) -> dict[str, Any]:
    manifest = manifest_result.get("manifest") if isinstance(manifest_result.get("manifest"), dict) else {}
    services = manifest.get("services") if isinstance(manifest.get("services"), list) else []
    for item in services:
        if isinstance(item, dict) and item.get("name") == name:
            return item
    return {}


def parsed(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("parsed") if isinstance(record.get("parsed"), dict) else {}
    return value


def excluded_boundary(model: dict[str, Any], name: str) -> dict[str, Any]:
    excluded = model.get("excluded_boundaries") if isinstance(model.get("excluded_boundaries"), list) else []
    for item in excluded:
        if isinstance(item, dict) and item.get("name") == name:
            return item
    return {}


def validate_manifest(manifest_result: dict[str, Any]) -> dict[str, bool]:
    service = service_by_name(manifest_result, "wsta-native-uplink-helper")
    manifest = manifest_result.get("manifest") if isinstance(manifest_result.get("manifest"), dict) else {}
    return {
        "decision_pass": manifest_result.get("decision") == "wsta90-service-hardening-manifest-source-pass",
        "service_present": bool(service),
        "service_boundary_preserve": service.get("status") == "boundary-preserve",
        "service_target_native_boundary": (
            service.get("target_user") == "root-native-boundary"
            and service.get("target_group") == "root-native-boundary"
        ),
        "service_network_native_owned": service.get("network_intent") == "native-owned-wifi-control-only",
        "service_seccomp_boundary_class": service.get("seccomp_profile") == "native-uplink-boundary",
        "service_no_ambient_caps": service.get("ambient_capabilities") == []
        and service.get("bounding_capabilities") == [],
        "global_default_public_off": (
            manifest.get("global_policy", {}).get("default_public_off") is True
        ),
        "redaction_clean": not bool(wsta154.wsta153.wsta108.redaction_findings({
            "service": service,
            "policy": {
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        })),
    }


def validate_wsta22_live(result: dict[str, Any]) -> dict[str, bool]:
    status = parsed(result.get("helper_status") if isinstance(result.get("helper_status"), dict) else {})
    scan = parsed(result.get("helper_scan") if isinstance(result.get("helper_scan"), dict) else {})
    safety = result.get("safety") if isinstance(result.get("safety"), dict) else {}
    checks = result.get("checks") if isinstance(result.get("checks"), dict) else {}
    return {
        "decision_pass": result.get("decision") == "wsta22-native-wifi-service-client-pass",
        "helper_status_pass": checks.get("helper_status_pass") is True,
        "helper_scan_pass": checks.get("helper_scan_pass") is True,
        "service_start_stop_pass": (
            checks.get("service_start_pass") is True and checks.get("service_stop_pass") is True
        ),
        "final_selftest_fail_zero": checks.get("final_selftest_fail_zero") is True,
        "status_owner_native": status.get("owner") == "native-init",
        "scan_owner_native": scan.get("owner") == "native-init",
        "status_op_only": status.get("op") == "status",
        "scan_op_only": scan.get("op") == "scan",
        "status_client_pass": status.get("native_wifi_service_client_decision")
        == "native-wifi-service-client-pass",
        "scan_client_pass": scan.get("native_wifi_service_client_decision")
        == "native-wifi-service-client-pass",
        "status_no_credentials_or_public": (
            status.get("credentials") == "0"
            and status.get("dhcp_routing") == "0"
            and status.get("public_tunnel") == "0"
            and status.get("native_wifi_service_client_secret_values_logged") == "0"
        ),
        "scan_redacted_no_connect_or_public": (
            scan.get("credentials") == "0"
            and scan.get("connect") == "0"
            and scan.get("dhcp_routing") == "0"
            and scan.get("public_tunnel") == "0"
            and scan.get("raw_results_redacted") == "1"
            and scan.get("native_wifi_service_client_secret_values_logged") == "0"
        ),
        "safety_supported_ops_status_scan": safety.get("service_supported_ops") == ALLOWED_DEBIAN_OPS,
        "safety_no_association_dhcp_ping_public": (
            safety.get("wifi_association") is False
            and safety.get("dhcp") is False
            and safety.get("ping") is False
            and safety.get("public_tunnel") is False
            and safety.get("userdata_touch") is False
            and safety.get("switch_root") is False
        ),
    }


def validate_seccomp_exclusion(model: dict[str, Any]) -> dict[str, bool]:
    uplink = excluded_boundary(model, "wsta-native-uplink-helper")
    hud = excluded_boundary(model, "native-dpublic-hud-presenter")
    return {
        "schema_ok": model.get("schema") == "a90-wsta154-seccomp-launcher-gate-model-v1",
        "state_ok": model.get("state") == "SECCOMP_LAUNCHER_DRY_RUN_GATE_MODEL_SOURCE_DEFINED",
        "model_only_not_enforced": model.get("enforcement_state") == "MODEL_ONLY_NOT_ENFORCED",
        "native_uplink_excluded": bool(uplink),
        "native_uplink_not_launchable_under_debian_seccomp": (
            uplink.get("launchable_under_debian_service_seccomp") is False
        ),
        "native_hud_presenter_still_excluded": (
            hud.get("launchable_under_debian_service_seccomp") is False
        ),
    }


def validate_helper_source(text: str) -> dict[str, bool]:
    return {
        "allows_only_status_scan_case": "status|scan)" in text,
        "denies_connect_associate_dhcp_ping_tunnel": all(op in text for op in DENIED_DEBIAN_OPS),
        "denies_before_request_write": text.find("native-wifi-service-op-denied") < text.find("request_tmp="),
        "publishes_seq_op_scan_delay": all(
            marker in text
            for marker in ["printf 'seq=%s\\n'", "printf 'op=%s\\n'", "printf 'scan_delay_ms=%s\\n'"]
        ),
        "requires_native_owner": 'if [ "$owner" != "native-init" ]; then' in text,
        "requires_matching_seq_op": '"$response_seq" != "$seq_value"' in text
        and '"$response_op" != "$op"' in text,
        "redacted_output_allowlist": all(key in text for key in RESPONSE_ALLOWLIST_KEYS),
        "secret_values_logged_zero": "native_wifi_service_client_secret_values_logged=0" in text,
    }


def build_policy(manifest_path: Path,
                 wsta22_path: Path,
                 wsta154_model_path: Path,
                 helper_source_path: Path) -> dict[str, Any]:
    return {
        "schema": POLICY_SCHEMA,
        "state": POLICY_STATE,
        "service": "wsta-native-uplink-helper",
        "classification": "native-owned-root-boundary",
        "source_evidence": {
            "service_hardening_manifest": rel(manifest_path),
            "native_wifi_service_live_proof": rel(wsta22_path),
            "seccomp_launcher_exclusion_model": rel(wsta154_model_path),
            "debian_client_source": rel(helper_source_path),
        },
        "boundary_contract": {
            "owner": "native-init",
            "credential_owner": "native-init",
            "debian_surface": "/usr/local/bin/a90-native-wifi-service-client",
            "debian_allowed_ops": ALLOWED_DEBIAN_OPS,
            "debian_denied_ops": DENIED_DEBIAN_OPS,
            "response_owner_required": "native-init",
            "response_keys_allowlist": RESPONSE_ALLOWLIST_KEYS,
            "debian_may_start_association": False,
            "debian_may_run_dhcp": False,
            "debian_may_ping_or_route": False,
            "debian_may_start_public_tunnel": False,
            "debian_may_read_wifi_credentials": False,
        },
        "launcher_policy": {
            "launchable_under_debian_service_launcher": False,
            "launchable_under_debian_service_seccomp": False,
            "reason": "native-owned credential, association, DHCP, routing, and Wi-Fi control boundary",
        },
        "live_proven_surface": {
            "status": {
                "op": "status",
                "owner": "native-init",
                "client_decision": "native-wifi-service-client-pass",
                "secrets_logged": 0,
            },
            "scan": {
                "op": "scan",
                "owner": "native-init",
                "client_decision": "native-wifi-service-client-pass",
                "raw_results_redacted": True,
                "secrets_logged": 0,
            },
        },
        "future_rungs": [
            {
                "name": "native-owned-connect-association-dhcp-service",
                "required_for": "Wi-Fi uplink beyond status/scan",
                "requires_operator_gate": True,
                "credential_handling": "native-owned-only",
            },
            {
                "name": "public-exposure-uplink-start",
                "required_for": "persistent public tunnel over Wi-Fi",
                "requires_operator_gate": True,
                "preconditions": [
                    "packet-filter default-drop",
                    "public exposure explicit gate",
                    "no credential values in committed artifacts",
                ],
            },
        ],
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_policy(policy: dict[str, Any]) -> dict[str, bool]:
    boundary = policy.get("boundary_contract") if isinstance(policy.get("boundary_contract"), dict) else {}
    launcher = policy.get("launcher_policy") if isinstance(policy.get("launcher_policy"), dict) else {}
    return {
        "schema_ok": policy.get("schema") == POLICY_SCHEMA,
        "state_ok": policy.get("state") == POLICY_STATE,
        "native_boundary_classification": policy.get("classification") == "native-owned-root-boundary",
        "allowed_ops_status_scan_only": boundary.get("debian_allowed_ops") == ALLOWED_DEBIAN_OPS,
        "denied_ops_cover_connectivity": set(DENIED_DEBIAN_OPS).issubset(
            set(boundary.get("debian_denied_ops") or [])
        ),
        "response_owner_native": boundary.get("response_owner_required") == "native-init",
        "debian_cannot_start_connectivity": all(
            boundary.get(key) is False
            for key in [
                "debian_may_start_association",
                "debian_may_run_dhcp",
                "debian_may_ping_or_route",
                "debian_may_start_public_tunnel",
                "debian_may_read_wifi_credentials",
            ]
        ),
        "launcher_not_debian_launchable": (
            launcher.get("launchable_under_debian_service_launcher") is False
            and launcher.get("launchable_under_debian_service_seccomp") is False
        ),
        "future_connect_rung_gated": all(
            isinstance(item, dict) and item.get("requires_operator_gate") is True
            for item in policy.get("future_rungs", [])
        ),
        "redaction_clean": not bool(wsta154.wsta153.wsta108.redaction_findings(policy)),
    }


def markdown(policy: dict[str, Any], result: dict[str, Any]) -> str:
    boundary = policy.get("boundary_contract", {})
    launcher = policy.get("launcher_policy", {})
    lines = [
        "# WSTA212 Native Uplink Boundary Policy",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- State: `{policy.get('state')}`",
        f"- Service: `{policy.get('service')}`",
        f"- Classification: `{policy.get('classification')}`",
        "- Device action: `false`",
        "",
        "## Debian Surface",
        "",
        f"- Client: `{boundary.get('debian_surface')}`",
        f"- Allowed ops: `{', '.join(boundary.get('debian_allowed_ops') or [])}`",
        f"- Denied ops: `{', '.join(boundary.get('debian_denied_ops') or [])}`",
        f"- Response owner required: `{boundary.get('response_owner_required')}`",
        "- Credentials visible to Debian: `false`",
        "- Public tunnel start from Debian helper: `false`",
        "",
        "## Launcher Policy",
        "",
        f"- Debian service launcher allowed: `{str(bool(launcher.get('launchable_under_debian_service_launcher'))).lower()}`",
        f"- Debian service seccomp target: `{str(bool(launcher.get('launchable_under_debian_service_seccomp'))).lower()}`",
        f"- Reason: `{launcher.get('reason')}`",
        "",
        "## Evidence",
        "",
    ]
    for key, value in policy.get("source_evidence", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Checks", ""])
    for key, value in result.get("checks", {}).items():
        lines.append(f"- {key}: `{str(bool(value)).lower()}`")
    lines.append("")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta212-native-uplink-boundary-policy-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    manifest_path = resolve_path(args.wsta90_service_hardening_manifest_json)
    wsta22_path = resolve_path(args.wsta22_native_wifi_service_client_json)
    wsta154_model_path = resolve_path(args.wsta154_seccomp_launcher_gate_model_json)
    helper_source_path = resolve_path(args.native_wifi_client_source)
    result: dict[str, Any] = {
        "scope": "WSTA212 host-only native uplink root-boundary policy",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.emit_native_uplink_boundary_policy),
            "private_run_dir": is_under(run_dir, PRIVATE_ROOT),
            "wsta90_manifest_private": is_under(manifest_path, PRIVATE_ROOT),
            "wsta22_result_private": is_under(wsta22_path, PRIVATE_ROOT),
            "wsta154_model_private": is_under(wsta154_model_path, PRIVATE_ROOT),
            "helper_source_public": is_under(helper_source_path, REPO_ROOT),
            "wsta90_manifest_present": manifest_path.is_file(),
            "wsta22_result_present": wsta22_path.is_file(),
            "wsta154_model_present": wsta154_model_path.is_file(),
            "helper_source_present": helper_source_path.is_file(),
        },
    }
    if not result["checks"]["explicit_gate"]:
        result["decision"] = "wsta212-blocked-explicit-gate-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    for key, decision in [
        ("private_run_dir", "wsta212-blocked-nonprivate-run-dir"),
        ("wsta90_manifest_private", "wsta212-blocked-wsta90-manifest-nonprivate"),
        ("wsta22_result_private", "wsta212-blocked-wsta22-result-nonprivate"),
        ("wsta154_model_private", "wsta212-blocked-wsta154-model-nonprivate"),
        ("helper_source_public", "wsta212-blocked-helper-source-outside-repo"),
        ("wsta90_manifest_present", "wsta212-blocked-wsta90-manifest-missing"),
        ("wsta22_result_present", "wsta212-blocked-wsta22-result-missing"),
        ("wsta154_model_present", "wsta212-blocked-wsta154-model-missing"),
        ("helper_source_present", "wsta212-blocked-helper-source-missing"),
    ]:
        if not result["checks"][key]:
            result["decision"] = decision
            result["gate_decision"] = decision
            result["ended_utc"] = utc_stamp()
            if result["checks"]["private_run_dir"]:
                run_dir.mkdir(parents=True, exist_ok=True)
                write_json(run_dir / SUMMARY_NAME, result)
            return result

    manifest_result = load_json(manifest_path)
    wsta22_result = load_json(wsta22_path)
    wsta154_model = load_json(wsta154_model_path)
    helper_source = helper_source_path.read_text(encoding="utf-8")
    validation = {
        "manifest": validate_manifest(manifest_result),
        "wsta22_live": validate_wsta22_live(wsta22_result),
        "seccomp_exclusion": validate_seccomp_exclusion(wsta154_model),
        "helper_source": validate_helper_source(helper_source),
    }
    result["validation"] = validation
    for section, checks in validation.items():
        result["checks"].update({f"{section}_{key}": value for key, value in checks.items()})
    if not all(all(checks.values()) for checks in validation.values()):
        result["decision"] = "wsta212-blocked-source-evidence-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(run_dir / SUMMARY_NAME, result)
        return result

    policy = build_policy(manifest_path, wsta22_path, wsta154_model_path, helper_source_path)
    policy_checks = validate_policy(policy)
    result["policy_checks"] = policy_checks
    result["checks"].update({f"policy_{key}": value for key, value in policy_checks.items()})
    result["decision"] = PASS_DECISION if all(policy_checks.values()) else "wsta212-blocked-policy-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["policy"] = {
        "schema": policy.get("schema"),
        "state": policy.get("state"),
        "service": policy.get("service"),
        "classification": policy.get("classification"),
        "allowed_ops": policy.get("boundary_contract", {}).get("debian_allowed_ops"),
        "denied_ops": policy.get("boundary_contract", {}).get("debian_denied_ops"),
        "debian_service_launcher_allowed": policy.get("launcher_policy", {}).get(
            "launchable_under_debian_service_launcher"
        ),
        "debian_service_seccomp_target": policy.get("launcher_policy", {}).get(
            "launchable_under_debian_service_seccomp"
        ),
    }
    result["ended_utc"] = utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / POLICY_NAME, policy)
    write_text(run_dir / MARKDOWN_NAME, markdown(policy, result))
    write_json(run_dir / SUMMARY_NAME, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta90-service-hardening-manifest-json", type=Path, default=DEFAULT_WSTA90_MANIFEST)
    parser.add_argument("--wsta22-native-wifi-service-client-json", type=Path, default=DEFAULT_WSTA22_RESULT)
    parser.add_argument("--wsta154-seccomp-launcher-gate-model-json", type=Path, default=DEFAULT_WSTA154_MODEL)
    parser.add_argument("--native-wifi-client-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("--emit-native-uplink-boundary-policy", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    result = run(args)
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 1


if __name__ == "__main__":
    raise SystemExit(main())
