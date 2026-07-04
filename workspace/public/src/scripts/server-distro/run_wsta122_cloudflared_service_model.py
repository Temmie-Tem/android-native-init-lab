#!/usr/bin/env python3
"""WSTA122 host-only cloudflared quick-tunnel service model.

This unit defines the hardening target for the D-public Cloudflare quick Tunnel
service.  It deliberately does not start a tunnel or treat prior tunnel
reachability as a hardening proof.  The target model is:

  * default public exposure stays off;
  * quick Tunnel starts only behind an explicit private gate;
  * cloudflared runs as non-root ``a90tunnel`` through the service launcher;
  * no-new-privs and zero effective capabilities are required;
  * the origin is loopback-only and the tunnel process is outbound-only;
  * public URL values remain private runtime artifacts and are never committed.

No device action, boot flash, native reboot, Wi-Fi association, DHCP, public
tunnel, packet-filter mutation, userdata write, or switch-root is performed.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import shlex
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
PASS_DECISION = "wsta122-cloudflared-service-model-source-pass"
RESULT_NAME = "wsta122_cloudflared_service_model.json"

SERVICE = "cloudflared-quick-tunnel"
USER = "a90tunnel"
BINARY = "/usr/local/bin/cloudflared"
QUICK_ENABLE = "/etc/a90-dpublic/cloudflared-quick-enable"
ORIGIN_URL = "http://127.0.0.1:8080"
METRICS_BIND = "127.0.0.1:0"
RUN_DIR = "/run/a90-dpublic"
PID_FILE = RUN_DIR + "/cloudflared-live.pid"
LOG_FILE = RUN_DIR + "/cloudflared-live.log"
URL_FILE = RUN_DIR + "/cloudflared-live.url"


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def safety() -> dict[str, Any]:
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
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def cloudflared_identity() -> dict[str, Any]:
    identity = dict(wsta3.SERVICE_IDENTITIES[SERVICE])
    return {
        "user": identity["user"],
        "group": identity["group"],
        "uid": identity["uid"],
        "gid": identity["gid"],
        "home": "/nonexistent",
        "shell": "/usr/sbin/nologin",
        "network_intent": identity["network_intent"],
    }


def cloudflared_command(origin_url: str = ORIGIN_URL,
                        metrics_bind: str = METRICS_BIND) -> list[str]:
    return [
        BINARY,
        "tunnel",
        "--no-autoupdate",
        "--url",
        origin_url,
        "--metrics",
        metrics_bind,
        "--loglevel",
        "info",
    ]


def launcher_command() -> list[str]:
    return [
        "/usr/local/bin/a90-service-launch",
        SERVICE,
        *cloudflared_command(),
    ]


def cloudflared_service_model() -> dict[str, Any]:
    ident = cloudflared_identity()
    command = cloudflared_command()
    return {
        "schema": "a90-wsta122-cloudflared-service-model-v1",
        "service": SERVICE,
        "state": "CLOUDFLARED_SERVICE_MODEL_SOURCE_DEFINED",
        "daemon": BINARY,
        "daemon_privilege_model": "non-root-outbound-client",
        "root_boundary_justification": "none-required; cloudflared should run as a90tunnel",
        "target_identity": ident,
        "default_exposure": {
            "public_default": "off",
            "start_requires_private_enable_file": QUICK_ENABLE,
            "start_requires_operator_live_gate": True,
            "boot_autostart_without_enable_file": False,
        },
        "network": {
            "origin_url": ORIGIN_URL,
            "origin_scope": "loopback-only",
            "metrics_bind": METRICS_BIND,
            "metrics_scope": "loopback-ephemeral",
            "outbound_tunnel_client": True,
            "public_inbound_listener": False,
            "packet_filter_precondition": "loopback-default-drop-before-public-start",
        },
        "command": command,
        "launcher_command": launcher_command(),
        "launcher_policy": {
            "required_launcher": "/usr/local/bin/a90-service-launch",
            "target_user": USER,
            "no_new_privs": True,
            "effective_capabilities": "zero",
            "direct_root_firstboot_start": "not-acceptable-for-always-on-profile",
        },
        "runtime_files": {
            "pid_file": PID_FILE,
            "log_file": LOG_FILE,
            "url_file": URL_FILE,
            "url_file_mode": "0600",
            "public_url_committable": False,
        },
        "credentials": {
            "quick_tunnel_accountless": True,
            "named_tunnel_credentials_required": False,
            "token_in_command": False,
            "secret_values_logged": 0,
        },
        "runtime_proof_required": [
            "prove process user/group is a90tunnel uid/gid 3902",
            "prove no-new-privs is set and CapEff is zero",
            "prove command includes tunnel --no-autoupdate --url http://127.0.0.1:8080",
            "prove public URL is captured only in a private runtime artifact",
            "prove no public URL or token appears in committed status/report output",
            "prove no inbound listener except loopback metrics/origin",
            "prove packet filter is applied before public exposure",
            "trace DNS/TLS/connect syscall set before seccomp enforcement",
            "prove cleanup removes cloudflared process and pid/log/url files",
        ],
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_model(model: dict[str, Any]) -> dict[str, bool]:
    ident = model.get("target_identity") if isinstance(model.get("target_identity"), dict) else {}
    exposure = model.get("default_exposure") if isinstance(model.get("default_exposure"), dict) else {}
    network = model.get("network") if isinstance(model.get("network"), dict) else {}
    launcher = model.get("launcher_policy") if isinstance(model.get("launcher_policy"), dict) else {}
    runtime = model.get("runtime_files") if isinstance(model.get("runtime_files"), dict) else {}
    credentials = model.get("credentials") if isinstance(model.get("credentials"), dict) else {}
    command = model.get("command") if isinstance(model.get("command"), list) else []
    launcher_cmd = model.get("launcher_command") if isinstance(model.get("launcher_command"), list) else []
    return {
        "schema_ok": model.get("schema") == "a90-wsta122-cloudflared-service-model-v1",
        "service_ok": model.get("service") == SERVICE,
        "non_root_user_ok": ident.get("user") == USER and ident.get("uid") == 3902 and ident.get("gid") == 3902,
        "nologin_identity_ok": ident.get("home") == "/nonexistent" and ident.get("shell") == "/usr/sbin/nologin",
        "root_boundary_not_required": model.get("daemon_privilege_model") == "non-root-outbound-client",
        "default_public_off": exposure.get("public_default") == "off",
        "explicit_enable_required": exposure.get("start_requires_private_enable_file") == QUICK_ENABLE,
        "operator_gate_required": exposure.get("start_requires_operator_live_gate") is True,
        "boot_autostart_without_enable_file_denied": exposure.get("boot_autostart_without_enable_file") is False,
        "origin_loopback_only": network.get("origin_url") == ORIGIN_URL
        and network.get("origin_scope") == "loopback-only",
        "metrics_loopback_ephemeral": network.get("metrics_bind") == METRICS_BIND
        and network.get("metrics_scope") == "loopback-ephemeral",
        "outbound_only": network.get("outbound_tunnel_client") is True
        and network.get("public_inbound_listener") is False,
        "packet_filter_precondition": network.get("packet_filter_precondition")
        == "loopback-default-drop-before-public-start",
        "command_no_autoupdate": "--no-autoupdate" in command,
        "command_origin_ok": "--url" in command and ORIGIN_URL in command,
        "command_metrics_loopback": "--metrics" in command and METRICS_BIND in command,
        "launcher_required": launcher.get("required_launcher") == "/usr/local/bin/a90-service-launch"
        and launcher_cmd[:2] == ["/usr/local/bin/a90-service-launch", SERVICE],
        "launcher_target_user": launcher.get("target_user") == USER,
        "launcher_no_new_privs_required": launcher.get("no_new_privs") is True,
        "launcher_caps_zero_required": launcher.get("effective_capabilities") == "zero",
        "direct_root_start_rejected_for_always_on": launcher.get("direct_root_firstboot_start")
        == "not-acceptable-for-always-on-profile",
        "url_file_private": runtime.get("url_file") == URL_FILE
        and runtime.get("url_file_mode") == "0600"
        and runtime.get("public_url_committable") is False,
        "no_named_tunnel_secret_required": credentials.get("quick_tunnel_accountless") is True
        and credentials.get("named_tunnel_credentials_required") is False
        and credentials.get("token_in_command") is False,
        "no_public_url_logged": model.get("public_url_value_logged") is False,
        "no_secret_values_logged": model.get("secret_values_logged") == 0,
    }


def model_passes(checks: dict[str, bool]) -> bool:
    return all(value is True for value in checks.values())


def launch_plan_shell() -> str:
    cmd = " ".join(shlex.quote(item) for item in launcher_command())
    return f"""
set -eu
echo A90WSTA122_CLOUDFLARED_MODEL_BEGIN
if [ ! -s {shlex.quote(QUICK_ENABLE)} ]; then
  echo A90WSTA122_QUICK_ENABLE_PRESENT=0
  echo A90WSTA122_CLOUDFLARED_MODEL_DONE
  exit 0
fi
echo A90WSTA122_QUICK_ENABLE_PRESENT=1
echo A90WSTA122_LAUNCHER_COMMAND={shlex.quote(cmd)}
echo A90WSTA122_EXPECT_USER={shlex.quote(USER)}
echo A90WSTA122_EXPECT_NO_NEW_PRIVS=1
echo A90WSTA122_EXPECT_CAPEFF_ZERO=1
echo A90WSTA122_ORIGIN_URL={shlex.quote(ORIGIN_URL)}
echo A90WSTA122_METRICS_BIND={shlex.quote(METRICS_BIND)}
echo A90WSTA122_URL_FILE={shlex.quote(URL_FILE)}
echo A90WSTA122_CLOUDFLARED_MODEL_DONE
""".strip()


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA122 host-only cloudflared quick-tunnel service model",
        "default_mode": "host-only-source-model",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--emit-cloudflared-model",
        ],
        "device_action": False,
        "public_tunnel": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta122-cloudflared-service-model-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    result: dict[str, Any] = {
        "scope": "WSTA122 host-only cloudflared quick-tunnel service model",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta122-blocked",
        "gate_decision": "not-run",
        "safety": safety(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta122-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / RESULT_NAME

    if not args.emit_cloudflared_model:
        result["decision"] = "wsta122-blocked-emit-cloudflared-model-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    model = cloudflared_service_model()
    checks = validate_model(model)
    result["cloudflared_service_model"] = model
    result["launch_plan_shell"] = launch_plan_shell()
    result["checks"] = checks
    if not model_passes(checks):
        result["decision"] = "wsta122-blocked-model-validation"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    result["decision"] = PASS_DECISION
    result["gate_decision"] = "ok"
    result["ended_utc"] = utc_stamp()
    write_json(out_json, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--emit-cloudflared-model", action="store_true")
    parser.add_argument("--print-template", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.print_template:
        print(json.dumps(template(), indent=2, sort_keys=True))
        return 0
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta122-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
