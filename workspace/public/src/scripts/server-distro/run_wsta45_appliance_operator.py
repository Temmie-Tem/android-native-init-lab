#!/usr/bin/env python3
"""WSTA45 operator-facing appliance wrapper for the native-uplink D-public path.

Default mode is a host-only preflight/menu surface.  The public publish path is
only available through an explicit operator gate, and it delegates to WSTA43 with
the WSTA44 native-uplink profile path enabled.  This wrapper never weakens the
WSTA43 native reboot, credentialed Wi-Fi, public exposure, or confirm-token gates.
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

import prepare_dpublic_preflight as dpublic  # noqa: E402
import run_wsta25_confirmed_autoconnect_live as wsta25  # noqa: E402
import run_wsta43_orchestrated_native_uplink_dpublic as wsta43  # noqa: E402


REPO_ROOT = wsta43.REPO_ROOT
DEFAULT_RUN_BASE = wsta43.DEFAULT_RUN_BASE
PROFILE_SOURCE = SCRIPT_DIR / "a90_dpublic_native_uplink_profile.sh"
PASS_DECISION = "wsta45-appliance-operator-wsta43-profile-pass"
PREFLIGHT_DECISION = "wsta45-appliance-operator-preflight-pass"
PUBLIC_CONFIRM_TOKEN = dpublic.DPUBLIC_LIVE_OPERATOR_TOKEN
FORBIDDEN_WSTA43_PASSTHROUGH = {
    "--allow-orchestrated-live",
    "--allow-native-reboot",
    "--allow-public-live",
    "--ack-credentialed-wifi",
    "--ack-public-exposure",
    "--native-confirm-token",
    "--public-confirm-token",
    "--use-native-uplink-profile",
}
NATIVE_CONFIRM_TOKEN_PLACEHOLDER = "<native-confirm-token>"
PUBLIC_CONFIRM_TOKEN_PLACEHOLDER = "<public-confirm-token>"


def script_relpath() -> str:
    return rel(Path(__file__).resolve())


def rel(path: Path) -> str:
    return wsta43.rel(path)


def write_json(path: Path, payload: Any) -> None:
    wsta43.write_json(path, payload)


def operator_publish_template() -> dict[str, Any]:
    command = [
        "python3",
        script_relpath(),
        "--mode",
        "publish",
        "--use-native-uplink-profile",
        "--allow-operator-live",
        "--allow-native-reboot",
        "--allow-public-live",
        "--ack-credentialed-wifi",
        "--ack-public-exposure",
        "--native-confirm-token",
        NATIVE_CONFIRM_TOKEN_PLACEHOLDER,
        "--public-confirm-token",
        PUBLIC_CONFIRM_TOKEN_PLACEHOLDER,
    ]
    return {
        "name": "publish-via-wsta43-profile",
        "command": command,
        "native_confirm_token_placeholder": NATIVE_CONFIRM_TOKEN_PLACEHOLDER,
        "public_confirm_token_placeholder": PUBLIC_CONFIRM_TOKEN_PLACEHOLDER,
        "secret_values_logged": 0,
        "public_url_value_logged": False,
        "notes": [
            "Fill token placeholders from the operator-approved private source at execution time.",
            "Optional WSTA43 passthrough args may follow a literal --, but gate flags are blocked there.",
        ],
    }


def operator_menu() -> list[dict[str, Any]]:
    return [
        {
            "name": "profile-preflight",
            "default": True,
            "public_exposure": False,
            "device_action": False,
            "description": "Validate the default-off native-uplink appliance profile surface.",
        },
        {
            "name": "publish-via-wsta43-profile",
            "default": False,
            "public_exposure": "explicit-gated",
            "device_action": "native-reboot-and-wsta43",
            "requires": [
                "--mode publish",
                "--use-native-uplink-profile",
                "--allow-operator-live",
                "--allow-native-reboot",
                "--allow-public-live",
                "--ack-credentialed-wifi",
                "--ack-public-exposure",
                "--native-confirm-token",
                "--public-confirm-token",
            ],
            "template": operator_publish_template(),
        },
    ]


def profile_contract() -> dict[str, Any]:
    if not PROFILE_SOURCE.is_file():
        return {"ok": False, "reason": "profile-source-missing", "path": rel(PROFILE_SOURCE)}
    text = PROFILE_SOURCE.read_text(encoding="utf-8")
    tunnel_phrase = "cloudflared" + " tunnel"
    return {
        "ok": True,
        "path": rel(PROFILE_SOURCE),
        "default_public_off": "native_uplink_profile_public_default=off" in text,
        "operator_enable_gate": "/etc/a90-dpublic/native-uplink-enable" in text,
        "confirmed_env_gate": (
            "A90_NATIVE_WIFI_UPLINK_ALLOW_CONFIRMED" in text
            and "A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN" in text
        ),
        "wsta43_required_marker": "native_uplink_profile_public_runner=wsta43" in text,
        "wsta45_wrapper_marker": "native_uplink_profile_operator_wrapper=wsta45" in text,
        "does_not_start_cloudflared": tunnel_phrase not in text,
        "secret_values_logged": 0,
    }


def explicit_publish_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if args.mode != "publish":
        return True, "ok"
    if not args.use_native_uplink_profile:
        return False, "wsta45-blocked-native-uplink-profile-required"
    if not args.allow_operator_live:
        return False, "wsta45-blocked-operator-live-allow-required"
    if not args.allow_native_reboot:
        return False, "wsta45-blocked-native-reboot-allow-required"
    if not args.allow_public_live:
        return False, "wsta45-blocked-public-live-allow-required"
    if not args.ack_credentialed_wifi:
        return False, "wsta45-blocked-credentialed-wifi-ack-required"
    if not args.ack_public_exposure:
        return False, "wsta45-blocked-public-exposure-ack-required"
    if args.native_confirm_token != wsta25.NATIVE_CONFIRM_TOKEN:
        return False, "wsta45-blocked-native-confirm-token-required"
    if args.public_confirm_token != PUBLIC_CONFIRM_TOKEN:
        return False, "wsta45-blocked-public-confirm-token-required"
    return True, "ok"


def normalize_passthrough(extra: list[str]) -> list[str]:
    if extra and extra[0] == "--":
        extra = extra[1:]
    for item in extra:
        option = item.split("=", 1)[0]
        if option in FORBIDDEN_WSTA43_PASSTHROUGH:
            raise ValueError(f"gate option must be supplied to WSTA45, not passthrough: {option}")
    return extra


def wsta43_args(args: argparse.Namespace, run_dir: Path) -> argparse.Namespace:
    nested = wsta43.build_arg_parser().parse_args(normalize_passthrough(list(args.wsta43_args or [])))
    nested.run_id = None
    nested.run_dir = run_dir / "wsta43-profile-publish"
    nested.allow_orchestrated_live = True
    nested.allow_native_reboot = True
    nested.allow_public_live = True
    nested.ack_credentialed_wifi = True
    nested.ack_public_exposure = True
    nested.native_confirm_token = args.native_confirm_token
    nested.public_confirm_token = args.public_confirm_token
    nested.use_native_uplink_profile = True
    return nested


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    nested = result.get("wsta43", {})
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "mode": result.get("mode"),
        "gate_decision": result.get("gate_decision"),
        "operator_publish_template": result.get("operator_publish_template", operator_publish_template()),
        "profile_contract": result.get("profile_contract", {}),
        "operator_menu": result.get("operator_menu", []),
        "checks": result.get("checks", {}),
        "wsta43": wsta43.public_summary(nested) if nested else None,
        "safety": result.get("safety", {}),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"wsta45-appliance-operator-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta45_result.json"

    profile = profile_contract()
    gate_ok, gate_decision = explicit_publish_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA45 appliance operator wrapper for native-uplink D-public publish",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "mode": args.mode,
        "operator_menu": operator_menu(),
        "operator_publish_template": operator_publish_template(),
        "profile_contract": profile,
        "gate_decision": gate_decision,
        "safety": {
            "boot_flash": False,
            "native_reboot": args.mode == "publish" and gate_ok and args.allow_native_reboot,
            "userdata_touch": False,
            "wifi_connect": "wsta43-profile-gated" if args.mode == "publish" else False,
            "public_tunnel": "wsta43-explicit-public-live-gated" if args.mode == "publish" else False,
            "native_confirm_token_value_logged": False,
            "public_confirm_token_value_logged": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
        "checks": {
            "profile_contract_ok": bool(
                profile.get("ok")
                and profile.get("default_public_off")
                and profile.get("operator_enable_gate")
                and profile.get("confirmed_env_gate")
                and profile.get("wsta43_required_marker")
                and profile.get("wsta45_wrapper_marker")
                and profile.get("does_not_start_cloudflared")
            ),
            "explicit_publish_gate": gate_ok,
            "use_native_uplink_profile": bool(args.use_native_uplink_profile),
            "allow_operator_live": bool(args.allow_operator_live),
            "allow_native_reboot": bool(args.allow_native_reboot),
            "allow_public_live": bool(args.allow_public_live),
            "ack_credentialed_wifi": bool(args.ack_credentialed_wifi),
            "ack_public_exposure": bool(args.ack_public_exposure),
            "native_confirm_token_supplied": bool(args.native_confirm_token),
            "native_confirm_token_matches": args.native_confirm_token == wsta25.NATIVE_CONFIRM_TOKEN,
            "public_confirm_token_supplied": bool(args.public_confirm_token),
            "public_confirm_token_matches": args.public_confirm_token == PUBLIC_CONFIRM_TOKEN,
        },
    }
    write_json(out_path, result)

    if not result["checks"]["profile_contract_ok"]:
        result["decision"] = "wsta45-blocked-profile-contract"
        result["ended_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        write_json(out_path, result)
        return result

    if args.mode == "preflight":
        result["decision"] = PREFLIGHT_DECISION
        result["ended_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        write_json(out_path, result)
        return result

    if not gate_ok:
        result["decision"] = gate_decision
        result["ended_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        write_json(out_path, result)
        return result

    nested = wsta43.run(wsta43_args(args, run_dir))
    result["wsta43"] = nested
    result["checks"]["wsta43_profile_requested"] = bool(
        nested.get("wsta42", {}).get("use_native_uplink_profile")
        or nested.get("wsta42", {}).get("checks", {}).get("use_native_uplink_profile")
    )
    result["checks"]["wsta43_pass"] = nested.get("decision") == wsta43.PASS_DECISION
    result["decision"] = PASS_DECISION if result["checks"]["wsta43_pass"] else "wsta45-blocked-wsta43-profile-publish"
    result["ended_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "publish"), default="preflight")
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--use-native-uplink-profile", action="store_true")
    parser.add_argument("--allow-operator-live", action="store_true")
    parser.add_argument("--allow-native-reboot", action="store_true")
    parser.add_argument("--allow-public-live", action="store_true")
    parser.add_argument("--ack-credentialed-wifi", action="store_true")
    parser.add_argument("--ack-public-exposure", action="store_true")
    parser.add_argument("--native-confirm-token", default="")
    parser.add_argument("--public-confirm-token", default="")
    parser.add_argument("--print-publish-template", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    parser.add_argument("wsta43_args", nargs=argparse.REMAINDER)
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.print_publish_template:
        print(json.dumps(operator_publish_template(), indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta45-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") in {PREFLIGHT_DECISION, PASS_DECISION} else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
