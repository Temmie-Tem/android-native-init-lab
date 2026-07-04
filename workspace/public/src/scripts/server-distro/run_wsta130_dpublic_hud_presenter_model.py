#!/usr/bin/env python3
"""WSTA130 host-only D-public HUD presenter architecture model.

WSTA129 proved that the WSTA127 direct non-root KMS design reaches display
discovery and then fails at ``SETCRTC`` with ``Permission denied``.  This unit
replaces that target with a split display contract:

  * Debian ``a90hud`` is only a non-root, no-network HUD intent producer;
  * it does not open DRM and never attempts KMS ``SETCRTC``;
  * a root/native-owned presenter keeps DRM master and owns KMS presentation;
  * the boundary between the two sides is a small bounded intent file with
    atomic update and strict schema parsing.

No device action, boot flash, native reboot, Wi-Fi association, DHCP, public
tunnel, packet-filter mutation, userdata write, DRM operation, KMS operation, or
switch-root is performed.
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
PASS_DECISION = "wsta130-dpublic-hud-presenter-model-source-pass"
RESULT_NAME = "wsta130_dpublic_hud_presenter_model.json"

SERVICE = "dpublic-hud"
INTENT_PRODUCER = "/usr/local/bin/a90-dpublic-hud-intent"
PRESENTER = "native-init-kms-presenter"
USER = "a90hud"
DRM_NODE = "/dev/dri/card0"
RUN_DIR = "/run/a90-dpublic"
INTENT_FILE = RUN_DIR + "/hud-intent.json"
INTENT_TMP = RUN_DIR + "/hud-intent.json.tmp"
PRESENTER_PID_FILE = RUN_DIR + "/hud-presenter.pid"
PRESENTER_LOG_FILE = RUN_DIR + "/hud-presenter.log"
MAX_INTENT_BYTES = 4096
STALE_AFTER_MS = 2000


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
        "network_intent": "no-network-display-intent-only",
    }


def intent_schema() -> dict[str, Any]:
    return {
        "schema": "a90-dpublic-hud-intent-v1",
        "max_bytes": MAX_INTENT_BYTES,
        "stale_after_ms": STALE_AFTER_MS,
        "atomic_update": {
            "tmp_path": INTENT_TMP,
            "final_path": INTENT_FILE,
            "operation": "write-fsync-rename",
            "mode": "0640",
        },
        "required_fields": {
            "schema": "literal:a90-dpublic-hud-intent-v1",
            "sequence": "u64-monotonic",
            "monotonic_ms": "u64",
        },
        "optional_fields": {
            "title": {"type": "ascii", "max_len": 32},
            "public_state": {"enum": ["PUBLIC_OFF", "PUBLIC_ARMED", "PUBLIC_LIVE"]},
            "upstream_state": {"enum": ["UNKNOWN", "NATIVE_UP", "NATIVE_DOWN"]},
            "service_state": {"enum": ["STARTING", "READY", "DEGRADED", "STOPPED"]},
            "packet_filter_state": {"enum": ["UNKNOWN", "READY", "APPLIED", "RESTORED"]},
            "cpu_millic": {"type": "u32", "max": 120000},
            "battery_percent": {"type": "u8", "max": 100},
            "lines": {"type": "ascii-list", "max_items": 6, "max_item_len": 48},
        },
        "forbidden_fields": [
            "command",
            "argv",
            "path",
            "shell",
            "url",
            "ssid",
            "psk",
            "token",
            "secret",
        ],
    }


def intent_producer_command() -> list[str]:
    return [
        "/usr/local/bin/a90-service-launch",
        SERVICE,
        INTENT_PRODUCER,
        "--output",
        INTENT_FILE,
    ]


def presenter_architecture_model() -> dict[str, Any]:
    ident = hud_identity()
    schema = intent_schema()
    return {
        "schema": "a90-wsta130-dpublic-hud-presenter-model-v1",
        "state": "DPUBLIC_HUD_PRESENTER_MODEL_SOURCE_DEFINED",
        "supersedes": {
            "wsta127_model": "non-root-drm-client",
            "wsta129_live_boundary": "setcrtc-permission-denied",
            "direct_nonroot_kms": "rejected-for-live-path",
        },
        "service": SERVICE,
        "debian_intent_producer": {
            "binary": INTENT_PRODUCER,
            "privilege_model": "non-root-intent-producer",
            "target_identity": ident,
            "launcher_command": intent_producer_command(),
            "launcher_policy": {
                "required_launcher": "/usr/local/bin/a90-service-launch",
                "target_user": USER,
                "no_new_privs": True,
                "effective_capabilities": "zero",
            },
            "display_access": {
                "opens_drm": False,
                "kms_setcrtc_allowed": False,
                "drm_fd_expected": False,
            },
            "network": {
                "opens_tcp_listener": False,
                "opens_udp_socket": False,
                "public_inbound_listener": False,
            },
        },
        "presenter": {
            "name": PRESENTER,
            "owner": "native-init",
            "privilege_model": "root-owned-kms-presenter",
            "kms_master_owner": True,
            "device_node": DRM_NODE,
            "allowed_kms_ops": [
                "DRM_IOCTL_MODE_GETRESOURCES",
                "DRM_IOCTL_MODE_GETCONNECTOR",
                "DRM_IOCTL_MODE_CREATE_DUMB",
                "DRM_IOCTL_MODE_ADDFB",
                "DRM_IOCTL_MODE_SETCRTC",
                "DRM_IOCTL_MODE_PAGE_FLIP",
                "DRM_IOCTL_MODE_RMFB",
                "DRM_IOCTL_MODE_DESTROY_DUMB",
            ],
            "forbidden_ops": [
                "exec-from-intent",
                "open-path-from-intent",
                "network-from-intent",
                "backlight-pmic-gpio-regulator",
            ],
            "runtime_files": {
                "pid_file": PRESENTER_PID_FILE,
                "log_file": PRESENTER_LOG_FILE,
                "log_file_committable": False,
            },
        },
        "boundary": {
            "transport": "bounded-atomic-json-intent-file",
            "intent_file": INTENT_FILE,
            "intent_schema": schema,
            "parser_policy": {
                "reject_unknown_fields": True,
                "ignore_stale_intent": True,
                "no_shell_expansion": True,
                "no_path_open_from_intent": True,
                "no_public_url_rendering": True,
            },
        },
        "default_exposure": {
            "public_default": "off",
            "network_autostart": False,
            "start_requires_operator_live_gate": True,
            "boot_autostart_without_presenter_policy": False,
        },
        "runtime_proof_required": [
            "prove Debian intent producer runs as a90hud uid/gid 3904",
            "prove Debian intent producer has no-new-privs and CapEff zero",
            "prove Debian intent producer has no DRM fd and no network socket",
            "prove presenter is the only process with DRM fd during HUD display",
            "prove presenter owns KMS SETCRTC/PAGE_FLIP and releases DRM on cleanup",
            "prove intent parser rejects forbidden fields and stale sequence/timestamp",
            "prove public URL values and credentials are not rendered or committed",
        ],
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_model(model: dict[str, Any]) -> dict[str, bool]:
    supersedes = model.get("supersedes") if isinstance(model.get("supersedes"), dict) else {}
    producer = (
        model.get("debian_intent_producer")
        if isinstance(model.get("debian_intent_producer"), dict)
        else {}
    )
    ident = (
        producer.get("target_identity")
        if isinstance(producer.get("target_identity"), dict)
        else {}
    )
    launcher = (
        producer.get("launcher_policy")
        if isinstance(producer.get("launcher_policy"), dict)
        else {}
    )
    display_access = (
        producer.get("display_access")
        if isinstance(producer.get("display_access"), dict)
        else {}
    )
    network = producer.get("network") if isinstance(producer.get("network"), dict) else {}
    presenter = model.get("presenter") if isinstance(model.get("presenter"), dict) else {}
    boundary = model.get("boundary") if isinstance(model.get("boundary"), dict) else {}
    intent = (
        boundary.get("intent_schema")
        if isinstance(boundary.get("intent_schema"), dict)
        else {}
    )
    atomic = intent.get("atomic_update") if isinstance(intent.get("atomic_update"), dict) else {}
    parser = (
        boundary.get("parser_policy")
        if isinstance(boundary.get("parser_policy"), dict)
        else {}
    )
    exposure = model.get("default_exposure") if isinstance(model.get("default_exposure"), dict) else {}
    launcher_cmd = (
        producer.get("launcher_command")
        if isinstance(producer.get("launcher_command"), list)
        else []
    )
    forbidden_fields = intent.get("forbidden_fields") if isinstance(intent.get("forbidden_fields"), list) else []
    allowed_ops = presenter.get("allowed_kms_ops") if isinstance(presenter.get("allowed_kms_ops"), list) else []
    forbidden_ops = presenter.get("forbidden_ops") if isinstance(presenter.get("forbidden_ops"), list) else []
    return {
        "schema_ok": model.get("schema") == "a90-wsta130-dpublic-hud-presenter-model-v1",
        "state_ok": model.get("state") == "DPUBLIC_HUD_PRESENTER_MODEL_SOURCE_DEFINED",
        "wsta129_boundary_acknowledged": supersedes.get("wsta129_live_boundary") == "setcrtc-permission-denied",
        "direct_nonroot_kms_rejected": supersedes.get("direct_nonroot_kms") == "rejected-for-live-path",
        "service_ok": model.get("service") == SERVICE,
        "producer_nonroot_identity_ok": (
            ident.get("user") == USER
            and ident.get("uid") == 3904
            and ident.get("gid") == 3904
            and ident.get("shell") == "/usr/sbin/nologin"
        ),
        "producer_launcher_shape_ok": launcher_cmd == intent_producer_command(),
        "producer_launcher_hardening_required": (
            launcher.get("required_launcher") == "/usr/local/bin/a90-service-launch"
            and launcher.get("target_user") == USER
            and launcher.get("no_new_privs") is True
            and launcher.get("effective_capabilities") == "zero"
        ),
        "producer_no_drm_or_kms": (
            display_access.get("opens_drm") is False
            and display_access.get("kms_setcrtc_allowed") is False
            and display_access.get("drm_fd_expected") is False
        ),
        "producer_no_network": (
            network.get("opens_tcp_listener") is False
            and network.get("opens_udp_socket") is False
            and network.get("public_inbound_listener") is False
        ),
        "presenter_root_native_owner": (
            presenter.get("owner") == "native-init"
            and presenter.get("privilege_model") == "root-owned-kms-presenter"
            and presenter.get("kms_master_owner") is True
        ),
        "presenter_drm_node_ok": presenter.get("device_node") == DRM_NODE,
        "presenter_kms_ops_bounded": (
            "DRM_IOCTL_MODE_SETCRTC" in allowed_ops
            and "DRM_IOCTL_MODE_PAGE_FLIP" in allowed_ops
            and "backlight-pmic-gpio-regulator" in forbidden_ops
            and "exec-from-intent" in forbidden_ops
        ),
        "intent_transport_bounded": (
            boundary.get("transport") == "bounded-atomic-json-intent-file"
            and boundary.get("intent_file") == INTENT_FILE
            and intent.get("schema") == "a90-dpublic-hud-intent-v1"
            and int(intent.get("max_bytes") or 0) <= MAX_INTENT_BYTES
            and int(intent.get("stale_after_ms") or 0) <= STALE_AFTER_MS
        ),
        "intent_atomic_update": (
            atomic.get("tmp_path") == INTENT_TMP
            and atomic.get("final_path") == INTENT_FILE
            and atomic.get("operation") == "write-fsync-rename"
            and atomic.get("mode") == "0640"
        ),
        "intent_secret_fields_forbidden": all(
            name in forbidden_fields for name in ("url", "ssid", "psk", "token", "secret")
        ),
        "intent_parser_fail_closed": (
            parser.get("reject_unknown_fields") is True
            and parser.get("ignore_stale_intent") is True
            and parser.get("no_shell_expansion") is True
            and parser.get("no_path_open_from_intent") is True
            and parser.get("no_public_url_rendering") is True
        ),
        "default_public_off": exposure.get("public_default") == "off",
        "operator_gate_required": exposure.get("start_requires_operator_live_gate") is True,
        "boot_autostart_without_policy_denied": (
            exposure.get("boot_autostart_without_presenter_policy") is False
        ),
        "no_public_url_logged": model.get("public_url_value_logged") is False,
        "no_secret_values_logged": model.get("secret_values_logged") == 0,
    }


def model_passes(checks: dict[str, bool]) -> bool:
    return all(value is True for value in checks.values())


def contract_plan_shell() -> str:
    producer_cmd = " ".join(shlex.quote(item) for item in intent_producer_command())
    return f"""
set -eu
echo A90WSTA130_HUD_PRESENTER_MODEL_BEGIN
echo A90WSTA130_WSTA129_BOUNDARY=setcrtc-permission-denied
echo A90WSTA130_DIRECT_NONROOT_KMS=rejected
echo A90WSTA130_INTENT_PRODUCER_COMMAND={shlex.quote(producer_cmd)}
echo A90WSTA130_INTENT_FILE={shlex.quote(INTENT_FILE)}
echo A90WSTA130_INTENT_MAX_BYTES={MAX_INTENT_BYTES}
echo A90WSTA130_PRESENTER_OWNER=native-init
echo A90WSTA130_PRESENTER_KMS_MASTER=1
echo A90WSTA130_PRODUCER_DRM_OPEN=0
echo A90WSTA130_PRODUCER_NETWORK=none
echo A90WSTA130_HUD_PRESENTER_MODEL_DONE
""".strip()


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA130 host-only D-public HUD presenter architecture model",
        "default_mode": "host-only-source-model",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--emit-presenter-model",
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
    run_id = args.run_id or f"wsta130-dpublic-hud-presenter-model-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    result: dict[str, Any] = {
        "scope": "WSTA130 host-only D-public HUD presenter architecture model",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta130-blocked",
        "gate_decision": "not-run",
        "safety": safety(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta130-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / RESULT_NAME

    if not args.emit_presenter_model:
        result["decision"] = "wsta130-blocked-emit-presenter-model-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    model = presenter_architecture_model()
    checks = validate_model(model)
    result["presenter_architecture_model"] = model
    result["contract_plan_shell"] = contract_plan_shell()
    result["checks"] = checks
    if not model_passes(checks):
        result["decision"] = "wsta130-blocked-model-validation"
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
    parser.add_argument("--emit-presenter-model", action="store_true")
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
        payload = {"decision": "wsta130-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
