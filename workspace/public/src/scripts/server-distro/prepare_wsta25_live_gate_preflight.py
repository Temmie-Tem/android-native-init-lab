#!/usr/bin/env python3
"""Prepare a redacted WSTA25 credentialed-live preflight.

This is host-only.  It validates that private Wi-Fi credentials are present and
well-formed, verifies the WSTA25 live runner surface, and emits only metadata
plus a redacted command template.  It never contacts the device and never writes
SSID/PSK/confirm-token values to the result.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta25_confirmed_autoconnect_live as wsta25  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WIFI_ENV = wsta3.DEFAULT_WIFI_ENV
RUNNER = SCRIPT_DIR / "run_wsta25_confirmed_autoconnect_live.py"
PASS_DECISION = "wsta25-credentialed-live-preflight-pass"
REDACTED_TOKEN = "<redacted:A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN>"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def redacted_wifi_env_status(path: Path) -> dict[str, Any]:
    loaded = wsta3.load_wifi_env(path)
    status: dict[str, Any] = {
        "path": rel(path),
        "exists": path.is_file(),
        "owner_private": wsta3.is_owner_private(path),
        "secret_values_logged": 0,
    }
    if not loaded.get("ok"):
        status.update({
            "ok": False,
            "reason": loaded.get("reason", "wifi-env-invalid"),
        })
        if "ssid_len" in loaded:
            status["ssid_len"] = loaded["ssid_len"]
        if "psk_len" in loaded:
            status["psk_len"] = loaded["psk_len"]
        return status

    psk = str(loaded["psk"])
    status.update({
        "ok": True,
        "reason": "ok",
        "ssid_present": True,
        "psk_present": True,
        "ssid_len": loaded["ssid_len"],
        "psk_len": loaded["psk_len"],
        "psk_format": "hex64" if re.fullmatch(r"[0-9a-fA-F]{64}", psk) else "passphrase",
    })
    return status


def runner_surface_status() -> dict[str, Any]:
    text = RUNNER.read_text(encoding="utf-8") if RUNNER.is_file() else ""
    return {
        "path": rel(RUNNER),
        "exists": RUNNER.is_file(),
        "explicit_gate": "--allow-confirmed-live" in text and "--ack-credentialed-wifi" in text,
        "confirm_token_arg": "--confirm-token" in text,
        "status_readiness_gate": "status_ready_for_confirmed_autoconnect" in text,
        "redacted_stdin_executor": "ssh_exec_redacted_script" in text and "input_redacted" in text,
        "no_public_tunnel": '"public_tunnel": False' in text and "cloudflared tunnel" not in text,
        "no_direct_wifi_connect": '["wifi", "connect"' not in text,
        "no_direct_dhcp_ping": '["wifi", "dhcp"' not in text and '["wifi", "ping"' not in text,
        "secret_values_logged": 0,
    }


def redacted_live_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        rel(RUNNER),
        "--allow-confirmed-live",
        "--ack-credentialed-wifi",
        "--confirm-token",
        REDACTED_TOKEN,
        "--service-dir",
        args.service_dir,
    ]


def run_default_dry_run(args: argparse.Namespace) -> dict[str, Any]:
    command = [sys.executable, str(RUNNER)]
    started = _dt.datetime.now(_dt.timezone.utc)
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=args.dry_run_timeout,
        check=False,
    )
    return {
        "command": [sys.executable, rel(RUNNER)],
        "returncode": completed.returncode,
        "stdout_decision": parse_json_decision(completed.stdout),
        "stderr": completed.stderr,
        "elapsed_wall_clock": (_dt.datetime.now(_dt.timezone.utc) - started).total_seconds(),
        "secret_values_logged": 0,
    }


def parse_json_decision(text: str) -> str:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return "unparseable"
    return str(payload.get("decision", "missing"))


def classify(result: dict[str, Any]) -> str:
    if not result.get("wifi_env", {}).get("ok"):
        return "wsta25-blocked-wifi-env"
    runner_status = result.get("runner_surface", {})
    for key in (
        "exists",
        "explicit_gate",
        "confirm_token_arg",
        "status_readiness_gate",
        "redacted_stdin_executor",
        "no_public_tunnel",
        "no_direct_wifi_connect",
        "no_direct_dhcp_ping",
    ):
        if not runner_status.get(key):
            return "wsta25-blocked-runner-surface"
    if result.get("default_dry_run", {}).get("stdout_decision") != "wsta25-blocked-explicit-live-allow-required":
        return "wsta25-blocked-runner-default-gate"
    if result.get("default_dry_run", {}).get("returncode") != 2:
        return "wsta25-blocked-runner-default-rc"
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"wsta25-credentialed-live-preflight-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    out_path = run_dir / "wsta25_preflight.json"

    result: dict[str, Any] = {
        "scope": "WSTA25 credentialed live host preflight",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wifi_env": redacted_wifi_env_status(args.wifi_env),
        "runner_surface": runner_surface_status(),
        "redacted_live_command": redacted_live_command(args),
        "public_exposure": "not-authorized",
        "device_contact": False,
        "association_attempted": False,
        "dhcp_attempted": False,
        "ping_attempted": False,
        "secret_values_logged": 0,
    }
    write_json(out_path, result)

    if args.run_default_dry_run:
        result["default_dry_run"] = run_default_dry_run(args)
    else:
        result["default_dry_run"] = {"skipped": True}
    result["decision"] = classify(result)
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--wifi-env", type=Path, default=DEFAULT_WIFI_ENV)
    parser.add_argument("--service-dir", default="/tmp/a90-native-wifi-uplink-service")
    parser.add_argument("--dry-run-timeout", type=float, default=10.0)
    parser.add_argument("--run-default-dry-run", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    result = run(args)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main())
