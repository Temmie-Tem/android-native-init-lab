#!/usr/bin/env python3
"""WSTA119 host-only Dropbear admin user model.

This unit defines the bounded admin path that must replace the temporary D2
root-authorized-keys model before any always-on server profile:

  * Dropbear remains a root-boundary auth daemon, explicitly justified as such;
  * root SSH login is disabled;
  * the operator key is installed for non-root ``a90admin`` only;
  * the daemon is bound to the USB/NCM admin address, not a public tunnel;
  * password auth and port forwarding are disabled.

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
PASS_DECISION = "wsta119-dropbear-admin-model-source-pass"
RESULT_NAME = "wsta119_dropbear_admin_model.json"
ADMIN_SERVICE = "dropbear-admin-usb"
ADMIN_USER = "a90admin"
ADMIN_HOME = "/home/a90admin"
ADMIN_SHELL = "/bin/sh"
ADMIN_AUTHORIZED_KEYS = ADMIN_HOME + "/.ssh/authorized_keys"
ROOT_AUTHORIZED_KEYS = "/root/.ssh/authorized_keys"
DEFAULT_BIND_IP = "192.168.7.2"
DEFAULT_PORT = 2222


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
        "admin_public_key_value_logged": False,
        "secret_values_logged": 0,
    }


def admin_identity() -> dict[str, Any]:
    identity = dict(wsta3.SERVICE_IDENTITIES[ADMIN_SERVICE])
    return {
        "user": identity["user"],
        "group": identity["group"],
        "uid": identity["uid"],
        "gid": identity["gid"],
        "home": ADMIN_HOME,
        "shell": ADMIN_SHELL,
        "authorized_keys": ADMIN_AUTHORIZED_KEYS,
        "authorized_keys_owner": f"{identity['uid']}:{identity['gid']}",
        "home_mode": "0700",
        "ssh_dir_mode": "0700",
        "authorized_keys_mode": "0600",
    }


def admin_passwd_line() -> str:
    ident = admin_identity()
    return (
        f"{ident['user']}:x:{ident['uid']}:{ident['gid']}:"
        f"A90 admin {ident['user']}:{ident['home']}:{ident['shell']}"
    )


def admin_placeholder_passwd_line() -> str:
    identity = wsta3.SERVICE_IDENTITIES[ADMIN_SERVICE]
    return (
        f"{identity['user']}:x:{identity['uid']}:{identity['gid']}:"
        f"A90 service {identity['user']}:/nonexistent:/usr/sbin/nologin"
    )


def admin_group_line() -> str:
    ident = admin_identity()
    return f"{ident['group']}:x:{ident['gid']}:"


def dropbear_command(bind_ip: str = DEFAULT_BIND_IP, port: int = DEFAULT_PORT) -> list[str]:
    return [
        "/usr/sbin/dropbear",
        "-F",
        "-E",
        "-r",
        "/tmp/a90_dropbear_admin_hostkey",
        "-p",
        f"{bind_ip}:{port}",
        "-P",
        "/tmp/a90_dropbear_admin.pid",
        "-s",
        "-w",
        "-j",
        "-k",
    ]


def dropbear_admin_model(bind_ip: str = DEFAULT_BIND_IP, port: int = DEFAULT_PORT) -> dict[str, Any]:
    ident = admin_identity()
    command = dropbear_command(bind_ip, port)
    return {
        "schema": "a90-wsta119-dropbear-admin-model-v1",
        "service": ADMIN_SERVICE,
        "state": "DROPBEAR_ADMIN_MODEL_SOURCE_DEFINED",
        "daemon": "/usr/sbin/dropbear",
        "daemon_privilege_model": "root-boundary-auth-daemon",
        "root_boundary_justification": (
            "Dropbear needs root for SSH authentication/session setup; "
            "the login target is the non-root a90admin account and root login is disabled."
        ),
        "target_identity": ident,
        "listen": {
            "bind_ip": bind_ip,
            "port": port,
            "scope": "usb-ncm-admin-only",
            "public_tunnel_allowed": False,
        },
        "auth": {
            "password_login": "disabled",
            "root_login": "disabled",
            "root_authorized_keys": "absent-required",
            "admin_authorized_keys": ident["authorized_keys"],
            "key_only": True,
        },
        "dropbear_options": command[1:],
        "dropbear_command": command,
        "forwarding": {
            "local_port_forwarding": "disabled",
            "remote_port_forwarding": "disabled",
        },
        "account_transition": {
            "may_replace_placeholder": admin_placeholder_passwd_line(),
            "required_passwd_line": admin_passwd_line(),
            "required_group_line": admin_group_line(),
            "conflict_policy": "fail-closed-on-any-other-existing-a90admin-entry",
        },
        "runtime_proof_required": [
            "start dropbear with -s -w -j -k on USB/NCM bind only",
            "prove SSH as a90admin returns uid/gid 3903",
            "prove root SSH login is rejected",
            "prove /root/.ssh/authorized_keys is absent",
            "prove cleanup removes dropbear and admin key material from the work image",
        ],
        "public_url_value_logged": False,
        "admin_public_key_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_model(model: dict[str, Any]) -> dict[str, bool]:
    ident = model.get("target_identity") if isinstance(model.get("target_identity"), dict) else {}
    listen = model.get("listen") if isinstance(model.get("listen"), dict) else {}
    auth = model.get("auth") if isinstance(model.get("auth"), dict) else {}
    forwarding = model.get("forwarding") if isinstance(model.get("forwarding"), dict) else {}
    options = model.get("dropbear_options") if isinstance(model.get("dropbear_options"), list) else []
    transition = (
        model.get("account_transition")
        if isinstance(model.get("account_transition"), dict)
        else {}
    )
    return {
        "schema_ok": model.get("schema") == "a90-wsta119-dropbear-admin-model-v1",
        "service_ok": model.get("service") == ADMIN_SERVICE,
        "root_boundary_justified": bool(model.get("root_boundary_justification")),
        "admin_user_ok": ident.get("user") == ADMIN_USER,
        "admin_uid_gid_ok": ident.get("uid") == 3903 and ident.get("gid") == 3903,
        "admin_home_not_root": ident.get("home") == ADMIN_HOME,
        "admin_shell_login_capable": ident.get("shell") == ADMIN_SHELL,
        "admin_authorized_keys_not_root": ident.get("authorized_keys") == ADMIN_AUTHORIZED_KEYS,
        "authorized_keys_mode_private": ident.get("authorized_keys_mode") == "0600",
        "usb_ncm_bind_only": listen.get("bind_ip") == DEFAULT_BIND_IP and listen.get("port") == DEFAULT_PORT,
        "public_tunnel_forbidden": listen.get("public_tunnel_allowed") is False,
        "password_login_disabled": auth.get("password_login") == "disabled" and "-s" in options,
        "root_login_disabled": auth.get("root_login") == "disabled" and "-w" in options,
        "root_authorized_keys_absent_required": auth.get("root_authorized_keys") == "absent-required",
        "port_forwarding_disabled": forwarding.get("local_port_forwarding") == "disabled"
        and forwarding.get("remote_port_forwarding") == "disabled"
        and "-j" in options
        and "-k" in options,
        "placeholder_transition_bounded": transition.get("may_replace_placeholder")
        == admin_placeholder_passwd_line(),
        "required_passwd_line_ok": transition.get("required_passwd_line") == admin_passwd_line(),
        "required_group_line_ok": transition.get("required_group_line") == admin_group_line(),
        "no_public_url_logged": model.get("public_url_value_logged") is False,
        "no_admin_public_key_value_logged": model.get("admin_public_key_value_logged") is False,
        "no_secret_values_logged": model.get("secret_values_logged") == 0,
    }


def model_passes(checks: dict[str, bool]) -> bool:
    return all(value is True for value in checks.values())


def admin_stage_script(public_key: str,
                       bind_ip: str = DEFAULT_BIND_IP,
                       port: int = DEFAULT_PORT) -> str:
    ident = admin_identity()
    command = " ".join(shlex.quote(item) for item in dropbear_command(bind_ip, port))
    return f"""
set -eu
echo A90WSTA119_ADMIN_MODEL_STAGE_BEGIN
ADMIN_USER={shlex.quote(ADMIN_USER)}
ADMIN_GROUP={shlex.quote(str(ident["group"]))}
ADMIN_UID={shlex.quote(str(ident["uid"]))}
ADMIN_GID={shlex.quote(str(ident["gid"]))}
ADMIN_HOME={shlex.quote(ADMIN_HOME)}
ADMIN_KEYS={shlex.quote(ADMIN_AUTHORIZED_KEYS)}
ROOT_KEYS={shlex.quote(ROOT_AUTHORIZED_KEYS)}
PASSWD_LINE={shlex.quote(admin_passwd_line())}
PLACEHOLDER_LINE={shlex.quote(admin_placeholder_passwd_line())}
GROUP_LINE={shlex.quote(admin_group_line())}
PUBKEY={shlex.quote(public_key)}
replace_or_append_line() {{
  file=$1
  name=$2
  expected=$3
  placeholder=$4
  if /bin/grep -q "^${{name}}:" "$file"; then
    existing=$(/bin/grep "^${{name}}:" "$file" | /usr/bin/head -n 1)
    if [ "$existing" = "$expected" ]; then
      return 0
    fi
    if [ "$existing" = "$placeholder" ]; then
      /bin/grep -v "^${{name}}:" "$file" > "$file.wsta119"
      /bin/printf '%s\\n' "$expected" >> "$file.wsta119"
      /bin/mv -f "$file.wsta119" "$file"
      return 0
    fi
    echo "A90WSTA119_ACCOUNT_CONFLICT name=$name"
    exit 64
  fi
  /bin/printf '%s\\n' "$expected" >> "$file"
}}
/bin/mkdir -p /etc "$ADMIN_HOME/.ssh" /root/.ssh
touch /etc/passwd /etc/group
replace_or_append_line /etc/group "$ADMIN_GROUP" "$GROUP_LINE" "$GROUP_LINE"
replace_or_append_line /etc/passwd "$ADMIN_USER" "$PASSWD_LINE" "$PLACEHOLDER_LINE"
/bin/chown "$ADMIN_UID:$ADMIN_GID" "$ADMIN_HOME" "$ADMIN_HOME/.ssh"
/bin/chmod 0700 "$ADMIN_HOME" "$ADMIN_HOME/.ssh"
/bin/printf '%s\\n' "$PUBKEY" > "$ADMIN_KEYS"
/bin/chown "$ADMIN_UID:$ADMIN_GID" "$ADMIN_KEYS"
/bin/chmod 0600 "$ADMIN_KEYS"
/bin/rm -f "$ROOT_KEYS"
if [ -e "$ROOT_KEYS" ]; then echo A90WSTA119_ROOT_AUTHORIZED_KEYS_ABSENT=0; exit 65; else echo A90WSTA119_ROOT_AUTHORIZED_KEYS_ABSENT=1; fi
if /bin/grep -qx "$PASSWD_LINE" /etc/passwd; then echo A90WSTA119_ADMIN_PASSWD_LINE=1; else echo A90WSTA119_ADMIN_PASSWD_LINE=0; exit 66; fi
if /bin/grep -qx "$GROUP_LINE" /etc/group; then echo A90WSTA119_ADMIN_GROUP_LINE=1; else echo A90WSTA119_ADMIN_GROUP_LINE=0; exit 67; fi
[ -s "$ADMIN_KEYS" ] && echo A90WSTA119_ADMIN_AUTHORIZED_KEYS=1 || {{ echo A90WSTA119_ADMIN_AUTHORIZED_KEYS=0; exit 68; }}
echo A90WSTA119_DROPBEAR_COMMAND={shlex.quote(command)}
echo A90WSTA119_ADMIN_MODEL_STAGE_DONE
""".strip()


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA119 host-only Dropbear admin user model",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--emit-admin-model",
            "--run-dir",
            "workspace/private/runs/server-distro/<wsta119-run>",
        ],
        "device_action": False,
        "boot_flash": False,
        "admin_public_key_value_logged": False,
        "secret_values_logged": 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta119-dropbear-admin-model-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    result: dict[str, Any] = {
        "scope": "WSTA119 host-only Dropbear admin user model",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta119-blocked",
        "gate_decision": "not-run",
        "safety": safety(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta119-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / RESULT_NAME
    if not args.emit_admin_model:
        result["decision"] = "wsta119-blocked-emit-admin-model-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    model = dropbear_admin_model(args.bind_ip, args.port)
    checks = validate_model(model)
    result["dropbear_admin_model"] = model
    result["checks"] = checks
    if not model_passes(checks):
        result["decision"] = "wsta119-blocked-admin-model-incomplete"
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
    parser.add_argument("--emit-admin-model", action="store_true")
    parser.add_argument("--bind-ip", default=DEFAULT_BIND_IP)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--print-template", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.print_template:
        print(json.dumps(template(), indent=2, sort_keys=True))
        return 0
    result = run(args)
    if args.print_full_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps({"decision": result.get("decision"), "run_dir": result.get("run_dir")}, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main_with_args())
