#!/usr/bin/env python3
"""WSTA154 host-only launcher-side seccomp dry-run gate model.

Consumes the WSTA153 source-only seccomp policy and emits a deterministic model
for wiring ``/usr/local/bin/a90-service-launch`` to a dry-run seccomp gate:

  * every launchable service must map to a concrete observed profile;
  * unknown or incomplete policy state blocks before exec;
  * filter loading stays disabled and explicitly future-gated.

This unit does not stage a rootfs, build a BPF filter, load seccomp, flash,
reboot, or touch the device.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_wsta153_seccomp_policy_source as wsta153  # noqa: E402


REPO_ROOT = wsta153.REPO_ROOT
PRIVATE_ROOT = wsta153.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta153.DEFAULT_RUN_BASE
DEFAULT_WSTA153_POLICY = (
    DEFAULT_RUN_BASE
    / "wsta153-seccomp-policy-source-20260705T1207KST"
    / "wsta153_seccomp_policy.json"
)
PASS_DECISION = "wsta154-seccomp-launcher-gate-model-source-pass"
RESULT_NAME = "wsta154_seccomp_launcher_gate_model.json"
SUMMARY_NAME = "wsta154_result.json"
MODEL_SCHEMA = "a90-wsta154-seccomp-launcher-gate-model-v1"
MODEL_STATE = "SECCOMP_LAUNCHER_DRY_RUN_GATE_MODEL_SOURCE_DEFINED"
MODEL_ENFORCEMENT_STATE = "MODEL_ONLY_NOT_ENFORCED"

EXPECTED_POLICY_SERVICES = {
    "dpublic-smoke-httpd",
    "cloudflared-quick-tunnel",
    "dropbear-admin-usb",
    "dpublic-hud-intent",
}
EXPECTED_LAUNCHER_SERVICES = {
    "dpublic-smoke-httpd",
    "cloudflared-quick-tunnel",
    "dropbear-admin-usb",
    "dpublic-hud",
}
SERVICE_BINDING_PLAN = [
    {
        "launcher_service": "dpublic-smoke-httpd",
        "policy_service": "dpublic-smoke-httpd",
        "scope": "loopback smoke HTTP service",
        "command_surface": "a90-service-launch dpublic-smoke-httpd ...",
    },
    {
        "launcher_service": "cloudflared-quick-tunnel",
        "policy_service": "cloudflared-quick-tunnel",
        "scope": "outbound tunnel client plus loopback origin",
        "command_surface": "a90-service-launch cloudflared-quick-tunnel ...",
    },
    {
        "launcher_service": "dropbear-admin-usb",
        "policy_service": "dropbear-admin-usb",
        "scope": "USB-NCM admin SSH root-boundary daemon",
        "command_surface": "a90-service-launch dropbear-admin-usb ...",
    },
    {
        "launcher_service": "dpublic-hud",
        "policy_service": "dpublic-hud-intent",
        "scope": "Debian HUD intent producer only; native presenter remains outside Debian seccomp",
        "command_surface": "a90-service-launch dpublic-hud /usr/local/bin/a90-dpublic-hud-intent ...",
    },
]


def rel(path: Path) -> str:
    return wsta153.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta153.is_under(path, root)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "packet_filter_mutation": False,
        "userdata_touch": False,
        "switch_root": False,
        "seccomp_filter_built": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "model": result.get("model", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def services_by_name(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    services = policy.get("services") if isinstance(policy.get("services"), list) else []
    return {
        str(item.get("service")): item
        for item in services
        if isinstance(item, dict) and item.get("service")
    }


def validate_policy_source(policy: dict[str, Any]) -> dict[str, bool]:
    wsta153_checks = wsta153.validate_policy(policy)
    by_name = services_by_name(policy)
    excluded_names = {
        str(item.get("name"))
        for item in policy.get("excluded_boundaries", [])
        if isinstance(item, dict) and item.get("name")
    }
    return {
        **{f"wsta153_{key}": value for key, value in wsta153_checks.items()},
        "state_from_live_baselines": policy.get("state") == "SECCOMP_POLICY_DRAFT_FROM_LIVE_BASELINES",
        "expected_policy_service_set": set(by_name) == EXPECTED_POLICY_SERVICES,
        "all_profiles_have_names": all(
            bool(item.get("profile_name")) for item in by_name.values()
        ),
        "all_profiles_have_stable_allowlist_count": all(
            isinstance(item.get("allowlist_count"), int)
            and item.get("allowlist_count") == len(item.get("allowlist", []))
            for item in by_name.values()
        ),
        "all_source_profiles_still_not_enforced": all(
            isinstance(item.get("enforcement"), dict)
            and item["enforcement"].get("enabled") is False
            for item in by_name.values()
        ),
        "native_uplink_excluded": "wsta-native-uplink-helper" in excluded_names,
        "native_hud_presenter_excluded": "native-dpublic-hud-presenter" in excluded_names,
        "redaction_clean": not bool(wsta153.wsta108.redaction_findings(policy)),
    }


def allowlist_digest(profile: dict[str, Any]) -> str:
    allowlist = profile.get("allowlist") if isinstance(profile.get("allowlist"), list) else []
    encoded = json.dumps(sorted(str(item) for item in allowlist), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def service_binding(policy_services: dict[str, dict[str, Any]],
                    plan: dict[str, str]) -> dict[str, Any]:
    policy_service = plan["policy_service"]
    profile = policy_services[policy_service]
    return {
        "launcher_service": plan["launcher_service"],
        "policy_service": policy_service,
        "policy_profile_name": profile.get("profile_name"),
        "policy_allowlist_count": profile.get("allowlist_count"),
        "policy_allowlist_sha256": allowlist_digest(profile),
        "policy_default_action": profile.get("default_action"),
        "policy_source_state": profile.get("source_state"),
        "identity": profile.get("identity"),
        "network_scope": profile.get("network_scope"),
        "scope": plan["scope"],
        "command_surface": plan["command_surface"],
        "dry_run_checks": {
            "service_known": True,
            "profile_exists": True,
            "allowlist_nonempty": bool(profile.get("allowlist")),
            "source_profile_not_enforced": profile.get("enforcement", {}).get("enabled") is False,
            "deny_by_default": profile.get("deny_by_default") is True,
        },
        "filter_load": {
            "enabled": False,
            "reason": "WSTA154 models launcher dry-run only; no seccomp filter is built or loaded",
            "future_live_gate_required": True,
        },
        "dry_run_markers": [
            "A90WSTA154_SECCOMP_POLICY_PRESENT=1",
            "A90WSTA154_SECCOMP_DRY_RUN_ONLY=1",
            "A90WSTA154_SECCOMP_FILTER_LOAD=0",
            f"A90WSTA154_SECCOMP_SERVICE={plan['launcher_service']}",
            f"A90WSTA154_SECCOMP_POLICY_SERVICE={policy_service}",
            f"A90WSTA154_SECCOMP_PROFILE={profile.get('profile_name')}",
            f"A90WSTA154_SECCOMP_ALLOWLIST_COUNT={profile.get('allowlist_count')}",
        ],
    }


def fail_closed_rules() -> list[dict[str, str]]:
    return [
        {
            "condition": "unknown launcher service",
            "action": "block before exec with blocked-unknown-service",
        },
        {
            "condition": "seccomp policy JSON missing or unreadable",
            "action": "block before exec; do not fall back to unprofiled launch in seccomp-gated mode",
        },
        {
            "condition": "launcher service has no mapped policy profile",
            "action": "block before exec and log missing-profile",
        },
        {
            "condition": "mapped profile has an empty allowlist or non-default-deny posture",
            "action": "block before exec and log invalid-profile",
        },
        {
            "condition": "source policy claims enforcement already enabled",
            "action": "block WSTA154 dry-run model; enforcement requires a separate live gate",
        },
        {
            "condition": "native boundary requested as Debian service seccomp target",
            "action": "block; native uplink helper and native HUD presenter stay outside this launcher gate",
        },
    ]


def build_launcher_gate_model(policy_path: Path, policy: dict[str, Any]) -> dict[str, Any]:
    policy_services = services_by_name(policy)
    bindings = [service_binding(policy_services, plan) for plan in SERVICE_BINDING_PLAN]
    return {
        "schema": MODEL_SCHEMA,
        "state": MODEL_STATE,
        "source_policy_json": rel(policy_path),
        "source_policy_schema": policy.get("schema"),
        "source_policy_state": policy.get("state"),
        "source_policy_enforcement_state": policy.get("enforcement_state"),
        "enforcement_state": MODEL_ENFORCEMENT_STATE,
        "launcher_integration": {
            "target": "/usr/local/bin/a90-service-launch",
            "service_hardening_policy": "/etc/a90-dpublic/service-hardening.json",
            "seccomp_policy_source": "/etc/a90-dpublic/seccomp-policy.json",
            "mode": "dry-run-before-filter-load",
            "filter_load_enabled": False,
            "exec_continues_after_dry_run_pass": True,
            "future_enforcement_gate_required": True,
            "future_enforcement_flag": "A90_SERVICE_LAUNCH_SECCOMP_ENFORCE=1",
        },
        "service_bindings": bindings,
        "service_binding_count": len(bindings),
        "default_action": "block-launch-if-policy-missing-or-invalid",
        "fail_closed_rules": fail_closed_rules(),
        "dry_run_global_markers": [
            "A90WSTA154_SECCOMP_POLICY_PRESENT=1",
            "A90WSTA154_SECCOMP_DRY_RUN_ONLY=1",
            "A90WSTA154_SECCOMP_FILTER_LOAD=0",
        ],
        "excluded_boundaries": [
            {
                "name": "wsta-native-uplink-helper",
                "launchable_under_debian_service_seccomp": False,
                "reason": "native-owned credential and Wi-Fi control boundary",
            },
            {
                "name": "native-dpublic-hud-presenter",
                "launchable_under_debian_service_seccomp": False,
                "reason": "native-init KMS owner; Debian launcher covers only dpublic-hud-intent",
            },
        ],
        "next_live_gate": {
            "required": True,
            "suggested_unit": "WSTA155",
            "scope": "stage launcher dry-run logging in a private rootfs/chroot before any filter load",
        },
        "redaction": {
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    }


def validate_model(model: dict[str, Any]) -> dict[str, bool]:
    bindings = model.get("service_bindings") if isinstance(model.get("service_bindings"), list) else []
    by_launcher = {
        str(item.get("launcher_service")): item
        for item in bindings
        if isinstance(item, dict) and item.get("launcher_service")
    }
    excluded = {
        str(item.get("name")): item
        for item in model.get("excluded_boundaries", [])
        if isinstance(item, dict) and item.get("name")
    }
    fail_closed = model.get("fail_closed_rules") if isinstance(model.get("fail_closed_rules"), list) else []
    return {
        "schema_ok": model.get("schema") == MODEL_SCHEMA,
        "state_ok": model.get("state") == MODEL_STATE,
        "model_only_not_enforced": model.get("enforcement_state") == MODEL_ENFORCEMENT_STATE,
        "source_policy_is_wsta153": model.get("source_policy_schema") == "a90-wsta153-seccomp-policy-source-v1",
        "source_policy_not_enforced": model.get("source_policy_enforcement_state") == "SOURCE_ONLY_NOT_ENFORCED",
        "launcher_target_expected": model.get("launcher_integration", {}).get("target") == "/usr/local/bin/a90-service-launch",
        "dry_run_mode": model.get("launcher_integration", {}).get("mode") == "dry-run-before-filter-load",
        "filter_load_disabled": model.get("launcher_integration", {}).get("filter_load_enabled") is False,
        "service_binding_count_four": len(bindings) == 4,
        "expected_launcher_services_present": set(by_launcher) == EXPECTED_LAUNCHER_SERVICES,
        "hud_launcher_maps_to_intent_profile": (
            by_launcher.get("dpublic-hud", {}).get("policy_service") == "dpublic-hud-intent"
        ),
        "all_bindings_have_nonempty_profiles": all(
            isinstance(item, dict)
            and bool(item.get("policy_profile_name"))
            and isinstance(item.get("policy_allowlist_count"), int)
            and item.get("policy_allowlist_count") > 0
            for item in bindings
        ),
        "all_binding_filter_load_disabled": all(
            isinstance(item, dict)
            and isinstance(item.get("filter_load"), dict)
            and item["filter_load"].get("enabled") is False
            for item in bindings
        ),
        "all_binding_dry_run_checks_pass": all(
            isinstance(item, dict)
            and isinstance(item.get("dry_run_checks"), dict)
            and all(item["dry_run_checks"].values())
            for item in bindings
        ),
        "global_dry_run_markers_present": {
            "A90WSTA154_SECCOMP_POLICY_PRESENT=1",
            "A90WSTA154_SECCOMP_DRY_RUN_ONLY=1",
            "A90WSTA154_SECCOMP_FILTER_LOAD=0",
        }.issubset(set(model.get("dry_run_global_markers", []))),
        "fail_closed_rules_present": len(fail_closed) >= 6,
        "native_uplink_excluded_not_launchable": (
            excluded.get("wsta-native-uplink-helper", {}).get("launchable_under_debian_service_seccomp")
            is False
        ),
        "native_hud_presenter_excluded_not_launchable": (
            excluded.get("native-dpublic-hud-presenter", {}).get("launchable_under_debian_service_seccomp")
            is False
        ),
        "redaction_clean": not bool(wsta153.wsta108.redaction_findings(model)),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta154-seccomp-launcher-gate-model-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    policy_path = resolve_path(args.wsta153_seccomp_policy_json)
    result: dict[str, Any] = {
        "scope": "WSTA154 host-only launcher-side seccomp dry-run gate model",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.emit_seccomp_launcher_gate_model),
            "private_run_dir": is_under(run_dir, PRIVATE_ROOT),
            "policy_json_private": is_under(policy_path, PRIVATE_ROOT),
            "policy_json_present": policy_path.is_file(),
        },
    }
    if not result["checks"]["explicit_gate"]:
        result["decision"] = "wsta154-blocked-explicit-gate-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta154-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not result["checks"]["policy_json_private"]:
        result["decision"] = "wsta154-blocked-policy-json-nonprivate"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not result["checks"]["policy_json_present"]:
        result["decision"] = "wsta154-blocked-policy-json-missing"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(run_dir / SUMMARY_NAME, result)
        return result

    policy = load_json(policy_path)
    policy_checks = validate_policy_source(policy)
    result["policy_checks"] = policy_checks
    result["checks"].update({f"policy_{key}": value for key, value in policy_checks.items()})
    if not all(policy_checks.values()):
        result["decision"] = "wsta154-blocked-policy-not-ready-for-launcher-gate"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(run_dir / SUMMARY_NAME, result)
        return result

    model = build_launcher_gate_model(policy_path, policy)
    model_checks = validate_model(model)
    result["model"] = {
        "schema": model.get("schema"),
        "state": model.get("state"),
        "enforcement_state": model.get("enforcement_state"),
        "service_binding_count": model.get("service_binding_count"),
        "launcher_target": model.get("launcher_integration", {}).get("target"),
        "filter_load_enabled": model.get("launcher_integration", {}).get("filter_load_enabled"),
        "next_live_gate": model.get("next_live_gate"),
    }
    result["model_checks"] = model_checks
    result["checks"].update({f"model_{key}": value for key, value in model_checks.items()})
    result["decision"] = PASS_DECISION if all(model_checks.values()) else "wsta154-blocked-model-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / RESULT_NAME, model)
    write_json(run_dir / SUMMARY_NAME, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta153-seccomp-policy-json", type=Path, default=DEFAULT_WSTA153_POLICY)
    parser.add_argument("--emit-seccomp-launcher-gate-model", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta154-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
