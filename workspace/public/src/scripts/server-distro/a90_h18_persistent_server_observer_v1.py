#!/usr/bin/env python3
"""Bounded authenticated observer for the live A90 H18 Debian server.

This process sends no payload and performs no reboot, handoff, flash, mount, or
device write.  It opens key-only SSH sessions over the fixed USB NCM endpoint
and reads only the exact PID1, mount, Dropbear, HUD, and Wi-Fi facts required by
the H18 persistent-server result.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any


SCHEMA = "a90-h18-persistent-server-observer-v1"
HOST = "192.168.7.2"
PORT = 2222
BEGIN = "A90H18_OBSERVER_BEGIN"
END = "A90H18_OBSERVER_END"
KEY_RE = re.compile(r"^[a-z0-9_]+$")
POSITIVE_RE = re.compile(r"^[1-9][0-9]*$")
NONNEGATIVE_RE = re.compile(r"^[0-9]+$")
EXPECTED_KEYS = frozenset(
    {
        "pid1_comm",
        "pid1_exe",
        "root_mount",
        "auth_mount",
        "auth_key_meta",
        "firstboot_mount",
        "hud_run_mount",
        "dropbear_pid",
        "dropbear_exe",
        "listener_count",
        "listener_owner",
        "hud_pid",
        "hud_exe",
        "hud_drm_fd_count",
        "hud_status_state",
        "hud_present_rc",
        "hud_last_sequence",
        "marker_autoreboot_sec",
        "marker_dropbear_started",
        "marker_hud_intent_written",
        "marker_hud_presenter_pid_valid",
        "marker_hud_presenter_started",
        "marker_hud_started",
        "marker_wifi_sta_decision",
        "wlan0_operstate",
        "wlan0_carrier",
    }
)


class ObserverError(RuntimeError):
    """Raised when H18 live facts are absent, ambiguous, or malformed."""


REMOTE_SCRIPT = r'''
set +e
marker_value() {
  key=$1
  /usr/bin/awk -F= -v wanted="$key" '
    $1 == wanted { count += 1; value = $2 }
    END { if (count == 1) print value; else print "__invalid_count_" count + 0 }
  ' /run/a90-d3-marker 2>/dev/null
}
dropbear_pid=$(cat /run/a90-d3-dropbear.pid 2>/dev/null || true)
case "$dropbear_pid" in ''|*[!0-9]*) dropbear_pid=0 ;; esac
listener_inodes=$(
  /usr/bin/awk '$2 == "0207A8C0:08AE" && $4 == "0A" { print $10 }' /proc/net/tcp 2>/dev/null
)
listener_count=$(printf '%s\n' "$listener_inodes" | /usr/bin/awk 'NF { count += 1 } END { print count + 0 }')
listener_owner=0
for inode in $listener_inodes; do
  for fd in /proc/$dropbear_pid/fd/*; do
    target=$(readlink "$fd" 2>/dev/null || true)
    [ "$target" = "socket:[$inode]" ] && listener_owner=1
  done
done
hud_pid=$(cat /run/a90-dpublic/hud-presenter.pid 2>/dev/null || true)
case "$hud_pid" in ''|*[!0-9]*) hud_pid=0 ;; esac
hud_drm_fd_count=0
for fd in /proc/$hud_pid/fd/*; do
  target=$(readlink "$fd" 2>/dev/null || true)
  case "$target" in *dri*|*card0*|*drm*) hud_drm_fd_count=$((hud_drm_fd_count + 1)) ;; esac
done
status_value() {
  key=$1
  /usr/bin/awk -F= -v wanted="$key" '
    $1 == wanted { count += 1; value = $2 }
    END { if (count == 1) print value; else print "__invalid_count_" count + 0 }
  ' /run/a90-dpublic/hud-presenter.status 2>/dev/null
}
echo A90H18_OBSERVER_BEGIN
echo pid1_comm=$(cat /proc/1/comm 2>/dev/null)
echo pid1_exe=$(readlink /proc/1/exe 2>/dev/null)
echo root_mount=$(/usr/bin/awk '$2 == "/" { print $1 "|" $3 "|" $4 }' /proc/mounts 2>/dev/null)
echo auth_mount=$(/usr/bin/awk '$2 == "/root/.ssh" { print $1 "|" $3 "|" $4 }' /proc/mounts 2>/dev/null)
echo auth_key_meta=$(/usr/bin/stat -c '%F|%a|%u|%g|%h|%s' /root/.ssh/authorized_keys 2>/dev/null)
echo firstboot_mount=$(/usr/bin/awk '$2 == "/etc/a90-d3-firstboot" { print $1 "|" $3 "|" $4 }' /proc/mounts 2>/dev/null)
echo hud_run_mount=$(/usr/bin/awk '$2 == "/run/a90-dpublic" { print $1 "|" $3 "|" $4 }' /proc/mounts 2>/dev/null)
echo dropbear_pid=$dropbear_pid
echo dropbear_exe=$(readlink /proc/$dropbear_pid/exe 2>/dev/null)
echo listener_count=$listener_count
echo listener_owner=$listener_owner
echo hud_pid=$hud_pid
echo hud_exe=$(readlink /proc/$hud_pid/exe 2>/dev/null)
echo hud_drm_fd_count=$hud_drm_fd_count
echo hud_status_state=$(status_value state)
echo hud_present_rc=$(status_value present_rc)
echo hud_last_sequence=$(status_value last_sequence)
echo marker_autoreboot_sec=$(marker_value autoreboot_sec)
echo marker_dropbear_started=$(marker_value dropbear_started)
echo marker_hud_intent_written=$(marker_value hud_intent_written)
echo marker_hud_presenter_pid_valid=$(marker_value hud_presenter_pid_valid)
echo marker_hud_presenter_started=$(marker_value hud_presenter_started)
echo marker_hud_started=$(marker_value hud_started)
echo marker_wifi_sta_decision=$(marker_value wifi_sta_decision)
echo wlan0_operstate=$(cat /sys/class/net/wlan0/operstate 2>/dev/null)
echo wlan0_carrier=$(cat /sys/class/net/wlan0/carrier 2>/dev/null)
echo A90H18_OBSERVER_END
true
'''.strip()


def _private_regular_key(path: Path) -> Path:
    private_root = (Path(__file__).resolve().parents[4] / "private").resolve()
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise ObserverError("observer key must stay under workspace/private") from exc
    stat_result = resolved.stat()
    if path.is_symlink() or not resolved.is_file() or stat_result.st_nlink != 1:
        raise ObserverError("observer key is not one regular private file")
    if stat_result.st_mode & 0o077:
        raise ObserverError("observer private key mode is too broad")
    return resolved


def ssh_command(key: Path, connect_timeout: float) -> list[str]:
    return [
        "ssh",
        "-i",
        str(key),
        "-p",
        str(PORT),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        f"ConnectTimeout={max(1, int(connect_timeout))}",
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "PreferredAuthentications=publickey",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "KbdInteractiveAuthentication=no",
        f"root@{HOST}",
        REMOTE_SCRIPT,
    ]


def exact_section(text: str) -> str:
    lines = text.splitlines()
    if lines.count(BEGIN) != 1 or lines.count(END) != 1:
        raise ObserverError("H18 observer transcript markers are not unique")
    begin = lines.index(BEGIN)
    end = lines.index(END)
    if end <= begin:
        raise ObserverError("H18 observer transcript marker order is invalid")
    return "\n".join(lines[begin + 1 : end]) + "\n"


def parse_facts(text: str) -> dict[str, str]:
    section = exact_section(text)
    facts: dict[str, str] = {}
    for line in section.splitlines():
        if "=" not in line:
            raise ObserverError("H18 observer fact line is malformed")
        key, value = line.split("=", 1)
        if KEY_RE.fullmatch(key) is None or key in facts:
            raise ObserverError("H18 observer fact keys are not exact")
        facts[key] = value
    if set(facts) != EXPECTED_KEYS:
        raise ObserverError("H18 observer fact set is not exact")
    return facts


def classify(text: str, returncode: int, visible_hud: bool) -> dict[str, Any]:
    if returncode != 0:
        raise ObserverError("authenticated H18 SSH observation failed")
    facts = parse_facts(text)
    root_parts = facts["root_mount"].split("|")
    auth_parts = facts["auth_mount"].split("|")
    auth_key_parts = facts["auth_key_meta"].split("|")
    firstboot_parts = facts["firstboot_mount"].split("|")
    hud_run_parts = facts["hud_run_mount"].split("|")
    root_options = set(root_parts[2].split(",")) if len(root_parts) == 3 else set()
    auth_options = set(auth_parts[2].split(",")) if len(auth_parts) == 3 else set()
    firstboot_options = (
        set(firstboot_parts[2].split(",")) if len(firstboot_parts) == 3 else set()
    )
    hud_run_options = (
        set(hud_run_parts[2].split(",")) if len(hud_run_parts) == 3 else set()
    )
    auth_key_size = (
        int(auth_key_parts[5])
        if len(auth_key_parts) == 6 and auth_key_parts[5].isdigit()
        else 0
    )
    exact = {
        "authenticated_ssh": True,
        "debian_pid1": facts["pid1_comm"] == "init" and facts["pid1_exe"] == "/usr/sbin/init",
        "ufs_root_read_only": (
            len(root_parts) == 3
            and root_parts[0] == "/dev/block/a90-userdata"
            and root_parts[1] == "ext4"
            and {"ro", "nosuid", "nodev"} <= root_options
            and bool({"noload", "norecovery"} & root_options)
        ),
        "observer_auth_tmpfs": (
            len(auth_parts) == 3
            and auth_parts[0] == "a90-h17-observer-auth"
            and auth_parts[1] == "tmpfs"
            and {"rw", "nosuid", "nodev", "noexec"} <= auth_options
            and auth_key_parts[:5] == ["regular file", "600", "0", "0", "1"]
            and 64 <= auth_key_size <= 512
        ),
        "firstboot_overlay": (
            len(firstboot_parts) == 3
            and {"ro", "nosuid", "nodev"} <= firstboot_options
        ),
        "hud_shared_run_tmpfs": (
            len(hud_run_parts) == 3
            and hud_run_parts[0] == "a90-dpublic-hud"
            and hud_run_parts[1] == "tmpfs"
            and {"rw", "nosuid", "nodev"} <= hud_run_options
            and "ro" not in hud_run_options
        ),
        "dropbear": (
            POSITIVE_RE.fullmatch(facts["dropbear_pid"]) is not None
            and facts["dropbear_exe"] == "/usr/sbin/dropbear"
            and facts["listener_count"] == "1"
            and facts["listener_owner"] == "1"
            and facts["marker_dropbear_started"] == "1"
        ),
        "native_hud_presenter": (
            POSITIVE_RE.fullmatch(facts["hud_pid"]) is not None
            and facts["hud_exe"] in {"/init", "/init (deleted)"}
            and POSITIVE_RE.fullmatch(facts["hud_drm_fd_count"]) is not None
            and facts["hud_status_state"] == "running"
            and facts["hud_present_rc"] == "0"
            and POSITIVE_RE.fullmatch(facts["hud_last_sequence"]) is not None
            and facts["marker_hud_intent_written"] == "1"
            and facts["marker_hud_presenter_pid_valid"] == "1"
            and facts["marker_hud_presenter_started"] == "1"
            and facts["marker_hud_started"] == "1"
        ),
        "wifi": (
            facts["marker_wifi_sta_decision"] == "wifi-sta-pass"
            and facts["wlan0_operstate"] in {"up", "unknown"}
            and facts["wlan0_carrier"] == "1"
        ),
        "persistent_no_autoreturn": facts["marker_autoreboot_sec"] == "disabled",
        "operator_visible_hud": visible_hud,
    }
    proof = all(exact.values())
    return {
        "schema": SCHEMA,
        "status": "PASS_A90_H18_PERSISTENT_SERVER_LIVE" if proof else "NO_PROOF_A90_H18_PERSISTENT_SERVER",
        "proof": proof,
        "device_safety": "HEALTH_PENDING_PERSISTENT_DEBIAN",
        "new_device_effect_authority": False,
        "automatic_native_return_expected": False,
        "facts": facts,
        "checks": exact,
        "transcript": text,
    }


def observe(
    key: Path,
    *,
    deadline_seconds: float,
    connect_timeout: float,
    visible_hud: bool,
) -> dict[str, Any]:
    deadline = time.monotonic() + deadline_seconds
    last: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "NO_PROOF_A90_H18_PERSISTENT_SERVER",
        "proof": False,
        "device_safety": "HEALTH_PENDING_PERSISTENT_DEBIAN",
        "new_device_effect_authority": False,
        "automatic_native_return_expected": False,
        "error": "observation not attempted",
    }
    attempts = 0
    while time.monotonic() < deadline:
        attempts += 1
        try:
            completed = subprocess.run(
                ssh_command(key, connect_timeout),
                text=True,
                capture_output=True,
                timeout=connect_timeout + 10.0,
                check=False,
            )
            transcript = completed.stdout + completed.stderr
            last = classify(transcript, completed.returncode, visible_hud)
            last["attempts"] = attempts
            if last["proof"]:
                return last
        except (OSError, subprocess.TimeoutExpired, ObserverError) as exc:
            last = {
                "schema": SCHEMA,
                "status": "NO_PROOF_A90_H18_PERSISTENT_SERVER",
                "proof": False,
                "device_safety": "HEALTH_PENDING_PERSISTENT_DEBIAN",
                "new_device_effect_authority": False,
                "automatic_native_return_expected": False,
                "attempts": attempts,
                "error": f"{type(exc).__name__}: {exc}",
            }
        time.sleep(2.0)
    return last


def write_private_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path = path.resolve()
    private_root = (Path(__file__).resolve().parents[4] / "private").resolve()
    try:
        path.relative_to(private_root)
    except ValueError as exc:
        raise ObserverError("observer output must stay under workspace/private") from exc
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists() or path.is_symlink():
        raise ObserverError("observer output must be absent")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp_name, path)
        dir_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observer-key", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--deadline-seconds", type=float, default=90.0)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--operator-visible-hud", action="store_true")
    args = parser.parse_args()
    if not 5.0 <= args.deadline_seconds <= 180.0:
        raise ObserverError("deadline must be between 5 and 180 seconds")
    if not 1.0 <= args.connect_timeout <= 15.0:
        raise ObserverError("connect timeout must be between 1 and 15 seconds")
    key = _private_regular_key(args.observer_key)
    result = observe(
        key,
        deadline_seconds=args.deadline_seconds,
        connect_timeout=args.connect_timeout,
        visible_hud=args.operator_visible_hud,
    )
    write_private_json_exclusive(args.output, result)
    print(json.dumps({key: value for key, value in result.items() if key != "transcript"}, sort_keys=True))
    return 0 if result["proof"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
