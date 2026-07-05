#!/usr/bin/env python3
"""WSTA227 private cloudflared egress route artifact builder.

WSTA226 requires a private DNS/TLS route artifact before it can run the
cloudflared egress allowlist live gate.  WSTA227 converts an attended private
route observation into that WSTA226 artifact schema while keeping raw route
values out of public output.

This unit is host-only.  It does not touch the device, flash, reboot, connect
Wi-Fi, run DHCP, open a public tunnel, mutate packet filters, write userdata,
switch root, mount a rootfs, or load an LSM profile.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import ipaddress
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_wsta226_cloudflared_egress_allowlist_execute_gate as wsta226  # noqa: E402


REPO_ROOT = wsta226.REPO_ROOT
PRIVATE_ROOT = wsta226.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta226.DEFAULT_RUN_BASE
PASS_DECISION = "wsta227-cloudflared-egress-route-artifact-source-pass"
OBSERVATION_SCHEMA = "a90-wsta227-cloudflared-egress-route-observation-v1"
OBSERVATION_STATE = "CLOUDFLARED_EGRESS_ROUTE_OBSERVED_PRIVATE"
RESULT_NAME = "wsta227_result.json"
ARTIFACT_NAME = "cloudflared_egress_route.json"
MARKDOWN_NAME = "wsta227_cloudflared_egress_route_artifact.md"


def rel(path: Path) -> str:
    return wsta226.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta226.is_under(path, root)


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


def get_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


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
        "lsm_profile_load": False,
        "route_values_logged": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "route_artifact": result.get("route_artifact_public", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def route_values(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalized_targets(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        candidate = value.strip()
        if "/" in candidate:
            normalized = str(ipaddress.ip_network(candidate, strict=False))
        else:
            normalized = str(ipaddress.ip_address(candidate))
        if ":" in normalized:
            raise ValueError("IPv6 targets are not supported by the current v4 helper")
        if normalized not in out:
            out.append(normalized)
    return out


def private_route_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": payload.get("schema"),
        "state": payload.get("state"),
        "dns4_count": len(route_values(payload, "dns4")),
        "tls4_count": len(route_values(payload, "tls4")),
        "source": payload.get("source"),
        "observed_at_utc": payload.get("observed_at_utc"),
        "route_values_private": payload.get("route_values_private") is True,
        "route_values_logged": False,
        "route_values_redacted": True,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_observation(payload: dict[str, Any]) -> dict[str, bool]:
    try:
        dns4 = normalized_targets(route_values(payload, "dns4"))
        tls4 = normalized_targets(route_values(payload, "tls4"))
        targets_valid = True
    except ValueError:
        dns4 = []
        tls4 = []
        targets_valid = False
    evidence = get_dict(payload, "evidence")
    return {
        "schema_ok": payload.get("schema") == OBSERVATION_SCHEMA,
        "state_ok": payload.get("state") == OBSERVATION_STATE,
        "source_private_runtime": payload.get("source") in {
            "attended-live-runtime",
            "operator-private-runtime-observation",
        },
        "dns4_present": bool(dns4),
        "tls4_present": bool(tls4),
        "targets_valid_v4": targets_valid,
        "resolver_observed": evidence.get("resolver_ready") is True,
        "dns_route_observed": evidence.get("dns_route_observed") is True,
        "tls_route_observed": evidence.get("tls_route_observed") is True,
        "route_values_private": payload.get("route_values_private") is True,
        "route_values_not_logged": payload.get("route_values_logged") is False,
        "public_url_not_logged": payload.get("public_url_value_logged") is False,
        "secrets_not_logged": payload.get("secret_values_logged") in (0, "0", None),
        "public_summary_redaction_clean": not bool(wsta226.wsta88.redaction_findings(private_route_summary(payload))),
    }


def build_wsta226_artifact(observation_path: Path, observation: dict[str, Any]) -> dict[str, Any]:
    dns4 = normalized_targets(route_values(observation, "dns4"))
    tls4 = normalized_targets(route_values(observation, "tls4"))
    return {
        "schema": wsta226.ROUTE_SCHEMA,
        "state": wsta226.ROUTE_STATE,
        "source_observation": rel(observation_path),
        "source": observation.get("source"),
        "observed_at_utc": observation.get("observed_at_utc"),
        "dns4": dns4,
        "tls4": tls4,
        "route_values_private": True,
        "route_values_logged": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def artifact_public(artifact_path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    summary = wsta226.route_summary(artifact)
    return {
        **summary,
        "path": rel(artifact_path),
        "wsta226_schema": artifact.get("schema") == wsta226.ROUTE_SCHEMA,
        "wsta226_state": artifact.get("state") == wsta226.ROUTE_STATE,
    }


def markdown(result: dict[str, Any]) -> str:
    artifact = get_dict(result, "route_artifact_public")
    return "\n".join([
        "# WSTA227 Cloudflared Egress Route Artifact",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Artifact: `{artifact.get('path')}`",
        f"- DNS route count: `{artifact.get('dns4_count')}`",
        f"- TLS route count: `{artifact.get('tls4_count')}`",
        "- Route values logged: `false`",
        "- Public URL logged: `false`",
        "",
    ])


def fail_result(result: dict[str, Any], out_path: Path, decision: str) -> dict[str, Any]:
    result["decision"] = decision
    result["gate_decision"] = decision
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def require_private_file(path_arg: Path | None, label: str) -> tuple[Path | None, str | None]:
    if path_arg is None:
        return None, f"wsta227-blocked-{label}-required"
    path = resolve_path(path_arg)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta227-blocked-{label}-nonprivate"
    if not path.is_file():
        return None, f"wsta227-blocked-{label}-missing"
    return path, None


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta227-cloudflared-egress-route-artifact-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    result: dict[str, Any] = {
        "scope": "WSTA227 private cloudflared egress route artifact builder",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta227-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
        "checks": {},
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta227-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / RESULT_NAME
    if not args.emit_route_artifact:
        return fail_result(result, out_path, "wsta227-blocked-explicit-emit-route-artifact-required")

    observation_path, path_error = require_private_file(args.route_observation_json, "route-observation")
    if path_error or observation_path is None:
        return fail_result(result, out_path, path_error or "wsta227-blocked-route-observation")
    observation = load_json(observation_path)
    observation_checks = validate_observation(observation)
    result["checks"] = {f"observation_{key}": value for key, value in observation_checks.items()}
    result["checks"]["observation_ready"] = all(observation_checks.values())
    result["observation_public"] = private_route_summary(observation)
    if not result["checks"]["observation_ready"]:
        return fail_result(result, out_path, "wsta227-blocked-route-observation-invalid")

    artifact = build_wsta226_artifact(observation_path, observation)
    artifact_checks = wsta226.validate_route_artifact(artifact)
    result["checks"].update({f"artifact_{key}": value for key, value in artifact_checks.items()})
    result["checks"]["artifact_ready_for_wsta226"] = all(artifact_checks.values())
    artifact_path = run_dir / ARTIFACT_NAME
    result["route_artifact_public"] = artifact_public(artifact_path, artifact)
    if not result["checks"]["artifact_ready_for_wsta226"]:
        return fail_result(result, out_path, "wsta227-blocked-route-artifact-invalid")

    findings = wsta226.wsta88.redaction_findings(public_summary(result)) + wsta226.wsta88.redaction_findings(markdown(result))
    if findings:
        result["gate_detail"] = {"findings": sorted(set(findings))}
        return fail_result(result, out_path, "wsta227-blocked-redaction-finding")

    result["decision"] = PASS_DECISION
    result["gate_decision"] = "ok"
    result["ended_utc"] = utc_stamp()
    write_json(artifact_path, artifact)
    write_json(out_path, result)
    write_text(run_dir / MARKDOWN_NAME, markdown(result))
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--emit-route-artifact", action="store_true")
    parser.add_argument("--route-observation-json", type=Path)
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        result = {"decision": "wsta227-runner-error", "error": str(exc)}
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
