#!/usr/bin/env python3
"""WSTA127 host-only D-public HUD service model.

This unit defines the hardening target for the Debian-side D-public HUD.  It
does not start the HUD, open DRM, switch root, or claim that the DRM/node policy
is live-proven.  The target model is:

  * public exposure stays off and no network port is opened;
  * the HUD runs as non-root ``a90hud`` through the service launcher;
  * no-new-privs and zero effective capabilities are required;
  * DRM access is limited to ``/dev/dri/card0`` with an explicit device-node
    ownership/group policy that still needs live proof;
  * KMS dumb-buffer ioctls must be traced before seccomp enforcement.

No device action, boot flash, native reboot, Wi-Fi association, DHCP, public
tunnel, packet-filter mutation, userdata write, DRM operation, or switch-root is
performed.
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
PASS_DECISION = "wsta127-dpublic-hud-service-model-source-pass"
RESULT_NAME = "wsta127_dpublic_hud_service_model.json"

SERVICE = "dpublic-hud"
USER = "a90hud"
BINARY = "/usr/local/bin/a90-dpublic-hud"
DRM_NODE = "/dev/dri/card0"
DRM_SYSFS_DEV = "/sys/class/drm/card0/dev"
RUN_DIR = "/run/a90-dpublic"
PID_FILE = RUN_DIR + "/dpublic-hud.pid"
LOG_FILE = RUN_DIR + "/dpublic-hud.log"


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
        "drm_open": False,
        "kms_setcrtc": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def hud_identity() -> dict[str, Any]:
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


def hud_command() -> list[str]:
    return [BINARY]


def launcher_command() -> list[str]:
    return [
        "/usr/local/bin/a90-service-launch",
        SERVICE,
        *hud_command(),
    ]


def hud_service_model() -> dict[str, Any]:
    ident = hud_identity()
    command = hud_command()
    return {
        "schema": "a90-wsta127-dpublic-hud-service-model-v1",
        "service": SERVICE,
        "state": "DPUBLIC_HUD_SERVICE_MODEL_SOURCE_DEFINED",
        "daemon": BINARY,
        "daemon_privilege_model": "non-root-drm-client",
        "root_boundary_justification": "none-required after DRM device-node policy is live-proven",
        "target_identity": ident,
        "default_exposure": {
            "public_default": "off",
            "network_autostart": False,
            "start_requires_operator_live_gate": True,
            "boot_autostart_without_device_policy": False,
        },
        "network": {
            "network_intent": "no-network-drm-output-only",
            "opens_tcp_listener": False,
            "opens_udp_socket": False,
            "public_inbound_listener": False,
            "requires_packet_filter": False,
        },
        "display": {
            "device_node": DRM_NODE,
            "device_source": DRM_SYSFS_DEV,
            "device_node_policy": "card0-owned-or-group-readable-by-a90hud-before-launch",
            "drm_master_required": True,
            "kms_surface": "dumb-framebuffer-xbgr8888",
            "render_scope": "status-hud-only",
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
            "pid_file_private": True,
            "log_file_committable": False,
        },
        "runtime_proof_required": [
            "prove process user/group is a90hud uid/gid 3904",
            "prove no-new-privs is set and CapEff is zero",
            "prove command is launched through a90-service-launch dpublic-hud",
            "prove /dev/dri/card0 policy lets a90hud open DRM without wider root",
            "prove HUD opens no non-loopback network socket and no public listener",
            "trace open/read/ioctl/mmap/munmap DRM syscall set before seccomp enforcement",
            "prove cleanup removes HUD process and runtime sidecars",
        ],
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_model(model: dict[str, Any]) -> dict[str, bool]:
    ident = model.get("target_identity") if isinstance(model.get("target_identity"), dict) else {}
    exposure = model.get("default_exposure") if isinstance(model.get("default_exposure"), dict) else {}
    network = model.get("network") if isinstance(model.get("network"), dict) else {}
    display = model.get("display") if isinstance(model.get("display"), dict) else {}
    launcher = model.get("launcher_policy") if isinstance(model.get("launcher_policy"), dict) else {}
    runtime = model.get("runtime_files") if isinstance(model.get("runtime_files"), dict) else {}
    command = model.get("command") if isinstance(model.get("command"), list) else []
    launcher_cmd = model.get("launcher_command") if isinstance(model.get("launcher_command"), list) else []
    return {
        "schema_ok": model.get("schema") == "a90-wsta127-dpublic-hud-service-model-v1",
        "service_ok": model.get("service") == SERVICE,
        "non_root_user_ok": ident.get("user") == USER and ident.get("uid") == 3904 and ident.get("gid") == 3904,
        "nologin_identity_ok": ident.get("home") == "/nonexistent" and ident.get("shell") == "/usr/sbin/nologin",
        "root_boundary_not_required": model.get("daemon_privilege_model") == "non-root-drm-client",
        "default_public_off": exposure.get("public_default") == "off",
        "operator_gate_required": exposure.get("start_requires_operator_live_gate") is True,
        "boot_autostart_without_device_policy_denied": exposure.get("boot_autostart_without_device_policy") is False,
        "no_network_autostart": exposure.get("network_autostart") is False,
        "no_network_listener": network.get("opens_tcp_listener") is False
        and network.get("opens_udp_socket") is False
        and network.get("public_inbound_listener") is False,
        "packet_filter_not_required_for_hud": network.get("requires_packet_filter") is False,
        "drm_node_policy_defined": display.get("device_node") == DRM_NODE
        and display.get("device_source") == DRM_SYSFS_DEV
        and display.get("device_node_policy") == "card0-owned-or-group-readable-by-a90hud-before-launch",
        "drm_master_required": display.get("drm_master_required") is True,
        "kms_surface_ok": display.get("kms_surface") == "dumb-framebuffer-xbgr8888",
        "command_shape_ok": command == [BINARY],
        "launcher_required": launcher.get("required_launcher") == "/usr/local/bin/a90-service-launch"
        and launcher_cmd[:2] == ["/usr/local/bin/a90-service-launch", SERVICE]
        and launcher_cmd[2:] == command,
        "launcher_target_user": launcher.get("target_user") == USER,
        "launcher_no_new_privs_required": launcher.get("no_new_privs") is True,
        "launcher_caps_zero_required": launcher.get("effective_capabilities") == "zero",
        "direct_root_start_rejected_for_always_on": launcher.get("direct_root_firstboot_start")
        == "not-acceptable-for-always-on-profile",
        "runtime_files_private": runtime.get("pid_file") == PID_FILE
        and runtime.get("log_file") == LOG_FILE
        and runtime.get("pid_file_private") is True
        and runtime.get("log_file_committable") is False,
        "no_public_url_logged": model.get("public_url_value_logged") is False,
        "no_secret_values_logged": model.get("secret_values_logged") == 0,
    }


def model_passes(checks: dict[str, bool]) -> bool:
    return all(value is True for value in checks.values())


def launch_plan_shell() -> str:
    cmd = " ".join(shlex.quote(item) for item in launcher_command())
    return f"""
set -eu
echo A90WSTA127_HUD_MODEL_BEGIN
echo A90WSTA127_LAUNCHER_COMMAND={shlex.quote(cmd)}
echo A90WSTA127_EXPECT_USER={shlex.quote(USER)}
echo A90WSTA127_EXPECT_NO_NEW_PRIVS=1
echo A90WSTA127_EXPECT_CAPEFF_ZERO=1
echo A90WSTA127_EXPECT_DRM_NODE={shlex.quote(DRM_NODE)}
echo A90WSTA127_EXPECT_NETWORK=none
echo A90WSTA127_HUD_MODEL_DONE
""".strip()


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA127 host-only D-public HUD service model",
        "default_mode": "host-only-source-model",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--emit-hud-model",
        ],
        "device_action": False,
        "public_tunnel": False,
        "drm_open": False,
        "kms_setcrtc": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta127-dpublic-hud-service-model-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    result: dict[str, Any] = {
        "scope": "WSTA127 host-only D-public HUD service model",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta127-blocked",
        "gate_decision": "not-run",
        "safety": safety(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta127-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / RESULT_NAME

    if not args.emit_hud_model:
        result["decision"] = "wsta127-blocked-emit-hud-model-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    model = hud_service_model()
    checks = validate_model(model)
    result["hud_service_model"] = model
    result["launch_plan_shell"] = launch_plan_shell()
    result["checks"] = checks
    if not model_passes(checks):
        result["decision"] = "wsta127-blocked-model-validation"
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
    parser.add_argument("--emit-hud-model", action="store_true")
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
        payload = {"decision": "wsta127-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
