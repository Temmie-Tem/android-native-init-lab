#!/usr/bin/env python3
"""Build an A/B-reproducible A90 Phase 3 Debian network/SSH profile.

The builder clones the exact Phase 2 display ext4 image and replaces only the
return-arm firstboot, a bounded Debian-owned NCM/Dropbear bootstrap, a bounded
observer for the native Wi-Fi handoff, inittab, and the stage description. It
is host-only, writes only below the private output root, and grants no candidate
or device authority.
"""

from __future__ import annotations

import argparse
import datetime as dt
import filecmp
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tomllib
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_phase2_display_v1_rootfs as phase2  # noqa: E402


PROFILE_DIR = SCRIPT_DIR / "phase3_network_ssh_v1"
MANIFEST_PATH = PROFILE_DIR / "manifest.toml"
PRIVATE_OUTPUTS = REPO_ROOT / "workspace/private/outputs"
SCHEMA = "a90-phase3-network-ssh-v1-rootfs"
PROFILE = "phase3-network-ssh-v1"
IMAGE_BYTES = 2 * 1024 * 1024 * 1024
FILESYSTEM_LABEL = "PHASE3NETSSHV1"
TARGETS = {
    "firstboot": "/etc/a90-d3-firstboot",
    "service": "/usr/local/sbin/a90-debian-network-ssh-v1",
    "wifi_handoff": "/usr/local/sbin/a90-debian-wifi-handoff-v1",
    "resolver_mountpoint": "/etc/resolv.conf",
    "inittab": "/etc/inittab",
    "stage": "/etc/a90-server-distro-stage",
}
RUNTIME_ABSENT = (
    "/root/.ssh/authorized_keys",
    "/etc/dropbear/dropbear_ed25519_host_key",
    "/run/a90-services/ready",
    "/run/a90-services/failure",
    "/run/a90-native-display-release",
    "/run/a90-display/ready",
    "/run/a90-display/failure",
    "/run/a90-wifi/ready",
    "/run/a90-wifi/failure",
)
HEX_DIGITS = frozenset("0123456789abcdef")


class ContractError(RuntimeError):
    """The Phase 3 network/SSH host profile is not closed."""


def sha256_file(path: Path) -> str:
    return phase2.sha256_file(path)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in HEX_DIGITS for character in value)
    ):
        raise ContractError(f"{label} is not one lowercase SHA256")
    return value


def resolve_repo_file(relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ContractError(f"{label} path is empty")
    path = (REPO_ROOT / relative).resolve()
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError as error:
        raise ContractError(f"{label} escapes repository") from error
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ContractError(f"{label} is not one regular file: {path}")
    return path


def require_pinned_file(
    table: dict[str, Any],
    path_key: str,
    sha_key: str,
    label: str,
) -> Path:
    path = resolve_repo_file(table.get(path_key), label)
    expected = require_sha256(table.get(sha_key), f"{label} pin")
    actual = sha256_file(path)
    if actual != expected:
        raise ContractError(
            f"{label} changed: got {actual}, expected {expected}"
        )
    return path


def load_manifest() -> tuple[dict[str, Any], str]:
    raw = MANIFEST_PATH.read_bytes()
    try:
        manifest = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ContractError("manifest is not valid UTF-8 TOML") from error
    if manifest.get("schema") != SCHEMA or manifest.get("profile") != PROFILE:
        raise ContractError("manifest schema or profile mismatch")
    if manifest.get("candidate_authority") is not False:
        raise ContractError("manifest must grant no candidate authority")
    if manifest.get("validation", {}).get("image_bytes") != IMAGE_BYTES:
        raise ContractError("manifest image size mismatch")
    if manifest.get("validation", {}).get("filesystem_label") != FILESYSTEM_LABEL:
        raise ContractError("manifest filesystem label mismatch")
    return manifest, sha256_bytes(raw)


def read_ext4_label(image: Path) -> str:
    with image.open("rb") as stream:
        stream.seek(1024 + 0x38)
        if stream.read(2) != b"\x53\xef":
            raise ContractError("base image is not ext4")
        stream.seek(1024 + 0x78)
        raw = stream.read(16)
    try:
        return raw.split(b"\0", 1)[0].decode("ascii")
    except UnicodeDecodeError as error:
        raise ContractError("ext4 label is not ASCII") from error


def validate_firstboot(text: str) -> tuple[str, ...]:
    issues: list[str] = []
    required = (
        "set -eu",
        "RETURN_SUPERVISOR=/usr/local/sbin/a90-d3-return-supervisor-v3405",
        'RETURN_SUPERVISOR_PID=$("$RETURN_SUPERVISOR" --arm 120 20)',
        "exit 71",
        "exit 72",
        'PID1_EXE=$(readlink /proc/1/exe 2>/dev/null || true)',
        'if [ "$PID1_EXE" != /usr/sbin/init ]',
        "exit 73",
        "schema=a90-phase3-network-ssh-v1-return-arm",
        "service_bootstrap=/usr/local/sbin/a90-debian-network-ssh-v1",
        'mv "$MARKER_TMP" "$MARKER"',
    )
    for token in required:
        if token not in text:
            issues.append(f"firstboot missing token: {token}")
    supervisor = text.find('RETURN_SUPERVISOR_PID=$("$RETURN_SUPERVISOR"')
    pid1 = text.find("PID1_EXE=$(readlink", supervisor + 1)
    marker = text.find("schema=a90-phase3-network-ssh-v1-return-arm", pid1 + 1)
    publish = text.find('mv "$MARKER_TMP" "$MARKER"', marker + 1)
    if min(supervisor, pid1, marker, publish) < 0 or not (
        supervisor < pid1 < marker < publish
    ):
        issues.append("firstboot return/PID1/marker order is not exact")
    for forbidden in (
        "ncm0",
        "dropbear",
        "ip addr",
        "while true",
        "\nsync\n",
        "/proc/sysrq-trigger",
        "/sbin/reboot",
    ):
        if forbidden in text:
            issues.append(f"firstboot contains delegated or unsafe token: {forbidden!r}")
    return tuple(issues)


def validate_service(text: str) -> tuple[str, ...]:
    issues: list[str] = []
    required = (
        "set -u",
        "RUN_DIR=/run/a90-services",
        "IFACE=ncm0",
        "NCM_ADDR=192.168.7.2/24",
        "NCM_PEER=192.168.7.1",
        "SSH_PORT=2222",
        "AUTHORIZED_KEYS=/root/.ssh/authorized_keys",
        "HOST_KEY=/etc/dropbear/dropbear_ed25519_host_key",
        "MAX_PID_POLLS=10",
        "MAX_CLEANUP_POLLS=5",
        "RESTORE_LINK_DOWN=0",
        "REMOVE_ADDR=0",
        "REMOVE_ROUTE=0",
        "REMOVE_HOST_KEY=0",
        "process_is_started_dropbear()",
        "listener_state_for_started_pid()",
        'if ! listener_snapshot=$("$TIMEOUT" 5 "$SS" -H -ltnp',
        'listener_snapshot=$("$TIMEOUT" 5 "$SS" -H -ltnp "sport = :$SSH_PORT"',
        'listener_owner="\\\"dropbear\\\",pid=$STARTED_PID,"',
        "return 2",
        "'') return 1",
        "*) return 3",
        "wait_for_dropbear_exit()",
        "cleanup_started_dropbear()",
        'kill "$STARTED_PID" 2>/dev/null || true',
        'kill -KILL "$STARTED_PID" 2>/dev/null || true',
        "wait_rc=$?",
        '[ ! -e "$DROPBEAR_PIDFILE" ] && [ ! -L "$DROPBEAR_PIDFILE" ]',
        "cleanup_network()",
        'route del "$NCM_PEER" dev "$IFACE"',
        'if cleanup_route=$("$TIMEOUT" 10 "$IP" route show exact',
        'addr del "$NCM_ADDR" dev "$IFACE"',
        'if cleanup_addr=$("$TIMEOUT" 10 "$IP" -o -4 addr show',
        'link set "$IFACE" down',
        'if cleanup_link=$("$TIMEOUT" 10 "$IP" -o link show',
        'if [ "$cleanup_flags" = "$cleanup_link" ]',
        "cleanup_host_key()",
        "schema=a90-debian-network-ssh-v1-failure",
        'echo dropbear_cleanup="$DROPBEAR_CLEANUP"',
        'echo network_cleanup="$NETWORK_CLEANUP"',
        'echo host_key_cleanup="$HOST_KEY_CLEANUP"',
        'PID1_EXE=$(readlink /proc/1/exe 2>/dev/null || true)',
        'if [ "$PID1_EXE" != /usr/sbin/init ]',
        'LINK_STATE=$("$TIMEOUT" 10 "$IP" -o link show dev "$IFACE"',
        "PRE_ADDR_STATE=",
        "PRE_ROUTE_STATE=",
        "ncm-pre-address-conflict",
        "ncm-pre-route-conflict",
        '"$TIMEOUT" 10 "$IP" link set "$IFACE" up',
        '"$TIMEOUT" 10 "$IP" addr replace "$NCM_ADDR" dev "$IFACE"',
        '"$TIMEOUT" 10 "$IP" route replace "$NCM_PEER" dev "$IFACE"',
        '[ ! -L "$AUTHORIZED_KEYS" ] || fail 89 authorized-keys-symlink',
        '[ -s "$AUTHORIZED_KEYS" ] || fail 89 authorized-keys-absent',
        "AUTH_META=$(\"$STAT\" -c '%u:%g:%a'",
        '[ ! -L "$HOST_KEY" ] || fail 90 host-key-symlink',
        '"$TIMEOUT" 20 /usr/bin/dropbearkey -t ed25519 -f "$HOST_KEY"',
        '/usr/sbin/dropbear -F -E -r "$HOST_KEY"',
        '-p "$NCM_IP:$SSH_PORT" -P "$DROPBEAR_PIDFILE" -s -j -k',
        "LAUNCHED_PID=$!",
        "STARTED_PID=$LAUNCHED_PID",
        'while [ "$poll" -lt "$MAX_PID_POLLS" ]',
        'if [ "$PIDFILE_PID" -ne "$LAUNCHED_PID" ]',
        'kill -0 "$STARTED_PID"',
        'readlink "/proc/$STARTED_PID/exe"',
        'LISTEN_STATE=$("$TIMEOUT" 10 "$SS" -H -ltnp "sport = :$SSH_PORT"',
        'LISTENER_OWNER="\\\"dropbear\\\",pid=$STARTED_PID,"',
        "dropbear-listener-owner-mismatch",
        "schema=a90-debian-network-ssh-v1-ready",
        "owner=debian-sysvinit",
        "dropbear_auth=public-key-only",
        "dropbear_forwarding=disabled",
        'mv "$READY_TMP" "$READY"',
        "WIFI_HANDOFF=/usr/local/sbin/a90-debian-wifi-handoff-v1",
        '"$WIFI_HANDOFF" >>"$WIFI_HANDOFF_LOG" 2>&1 &',
    )
    for token in required:
        if token not in text:
            issues.append(f"service missing token: {token}")
    ordered = (
        'PID1_EXE=$(readlink /proc/1/exe',
        '[ ! -L "$AUTHORIZED_KEYS" ]',
        '[ -s "$AUTHORIZED_KEYS" ]',
        "LINK_STATE=",
        "PRE_ADDR_STATE=",
        "PRE_ROUTE_STATE=",
        '"$TIMEOUT" 20 /usr/bin/dropbearkey',
        '"$TIMEOUT" 10 "$IP" link set "$IFACE" up',
        '"$TIMEOUT" 10 "$IP" addr replace',
        '\nADDR_STATE=$("$TIMEOUT" 10 "$IP"',
        '"$TIMEOUT" 10 "$IP" route replace',
        '\nROUTE_STATE=$("$TIMEOUT" 10 "$IP"',
        "/usr/sbin/dropbear -F -E",
        "LAUNCHED_PID=$!",
        "PIDFILE_PID=$(cat",
        'if [ "$PIDFILE_PID" -ne "$LAUNCHED_PID" ]',
        'kill -0 "$STARTED_PID"',
        "LISTEN_STATE=",
        "LISTENER_OWNER=",
        "schema=a90-debian-network-ssh-v1-ready",
        'mv "$READY_TMP" "$READY"',
        'if [ -x "$WIFI_HANDOFF" ]',
        '"$WIFI_HANDOFF" >>"$WIFI_HANDOFF_LOG" 2>&1 &',
    )
    positions = tuple(text.find(token) for token in ordered)
    if any(position < 0 for position in positions) or positions != tuple(
        sorted(positions)
    ):
        issues.append("service ownership and health-check order is not exact")
    for forbidden in (
        "while true",
        "mount ",
        "umount ",
        "dd ",
        "flash",
        "/proc/sysrq-trigger",
        "/sbin/reboot",
        "curl ",
        "wget ",
        "authorized_keys >",
        "PasswordAuth",
        "-a ",
    ):
        if forbidden in text:
            issues.append(f"service contains unsafe or out-of-scope token: {forbidden!r}")
    return tuple(issues)


def validate_wifi_handoff(text: str) -> tuple[str, ...]:
    issues: list[str] = []
    required = (
        "set -u",
        "RUN_DIR=/run/a90-wifi",
        "BRIDGE=/run/a90-native-wifi",
        "STATUS=$BRIDGE/status",
        "RESOLV=$BRIDGE/resolv.conf",
        "COMPANION=$BRIDGE/companion",
        "IFACE=wlan0",
        "MAX_POLLS=90",
        'while [ "$poll" -lt "$MAX_POLLS" ]',
        "schema=a90-native-wifi-handoff-v1",
        "decision=wifi-autoconnect-pass",
        "final_rc=0",
        "carrier_up=1",
        "default_route_present=1",
        "resolv_conf_present=1",
        "schema=a90-wifi-companion-health-v1",
        "required_children=alive",
        "modem_holder=alive",
        "companion-health-not-advancing",
        'route show default dev "$IFACE"',
        "RESOLV_META=$(\"$STAT\" -c '%u:%g:%a'",
        '[ "$RESOLV_META" = 0:0:600 ]',
        '"$MOUNT" --bind "$RESOLV" /etc/resolv.conf',
        'remount,bind,ro,nosuid,nodev,noexec',
        '"$FINDMNT" -n -o OPTIONS --target /etc/resolv.conf',
        "schema=a90-debian-wifi-handoff-v1-ready",
        "owner=debian-observer-native-control-plane",
        "control_plane=native-private-mount-namespace",
        "network_namespace=shared",
        "resolver_read_only=1",
        "companion_health=1",
        "companion_sequence_advanced=1",
        "ncm_ssh_affected=0",
        'mv "$READY_TMP" "$READY"',
    )
    for token in required:
        if token not in text:
            issues.append(f"wifi handoff missing token: {token}")
    for forbidden in (
        "while true",
        "wpa_supplicant",
        "wificond",
        "dhclient",
        "udhcpc",
        "iw ",
        "iwconfig",
        "ping ",
        "curl ",
        "wget ",
        "/cache/a90-wifi/",
        "/proc/sysrq-trigger",
        "/sbin/reboot",
    ):
        if forbidden in text:
            issues.append(f"wifi handoff contains delegated or unsafe token: {forbidden!r}")
    return tuple(issues)


def validate_inittab(text: str) -> tuple[str, ...]:
    required_lines = (
        "id:2:initdefault:",
        "si::sysinit:/etc/a90-d3-firstboot",
        "ns:2:wait:/usr/local/sbin/a90-debian-network-ssh-v1",
        "ds:2:once:/usr/local/sbin/a90-debian-display-launcher-v1",
        "ca:12345:ctrlaltdel:/sbin/reboot -f",
    )
    lines = tuple(
        line for line in text.splitlines()
        if line and not line.startswith("#")
    )
    if lines != required_lines:
        return (f"inittab lines differ: {lines!r}",)
    if "respawn" in text or "getty" in text or "openvt" in text:
        return ("inittab contains an unbounded or VT path",)
    return ()


def validate_stage(text: str) -> tuple[str, ...]:
    required = (
        "stage=D3 Phase3 network SSH v1 host profile",
        "return-supervisor=v3405-no-sync-decision",
        "network-owner=debian-sysvinit-wait",
        "ssh-daemon=dropbear-public-key-only",
        "display-owner=debian-direct-drm",
        "candidate-authority=none",
        "userdata=untouched",
    )
    return tuple(
        f"stage missing token: {token}" for token in required if token not in text
    )


def validate_tools() -> dict[str, str]:
    for tool in ("cp", "debugfs", "e2fsck", "tune2fs"):
        if shutil.which(tool) is None:
            raise ContractError(f"missing required host tool: {tool}")
    debugfs_version = phase2.run(["debugfs", "-V"]).stderr.decode().splitlines()[0]
    return {"debugfs": debugfs_version}


def require_private_regular(
    path: Path,
    *,
    expected_size: int | None = None,
    expected_sha256: str,
) -> os.stat_result:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ContractError(f"private input is not regular: {path}")
    if info.st_mode & 0o077:
        raise ContractError(f"private input permissions are too broad: {path}")
    if expected_size is not None and info.st_size != expected_size:
        raise ContractError(f"private input size changed: {path}")
    if sha256_file(path) != expected_sha256:
        raise ContractError(f"private input SHA256 changed: {path}")
    return info


def validate_base(manifest: dict[str, Any]) -> tuple[Path, Path]:
    base = manifest["base"]
    image = resolve_repo_file(base.get("image"), "base image")
    receipt = resolve_repo_file(base.get("receipt"), "base receipt")
    image_sha = require_sha256(base.get("image_sha256"), "base image pin")
    receipt_sha = require_sha256(base.get("receipt_sha256"), "base receipt pin")
    require_private_regular(
        image,
        expected_size=IMAGE_BYTES,
        expected_sha256=image_sha,
    )
    require_private_regular(receipt, expected_sha256=receipt_sha)
    try:
        receipt_value = json.loads(receipt.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError("base receipt is not valid JSON") from error
    if (
        not isinstance(receipt_value, dict)
        or receipt_value.get("schema") != "a90-phase2-display-v1-ab-receipt"
        or receipt_value.get("profile") != "phase2-display-v1"
        or receipt_value.get("candidate_authority") is not False
        or receipt_value.get("image_byte_identical") is not True
        or receipt_value.get("source_unchanged") is not True
        or receipt_value.get("host_only") is not True
        or receipt_value.get("device_action") is not False
        or receipt_value.get("flash") is not False
        or receipt_value.get("A", {}).get("image", {}).get("sha256") != image_sha
        or receipt_value.get("B", {}).get("image", {}).get("sha256") != image_sha
    ):
        raise ContractError("base Phase 2 receipt semantics are not exact")
    if read_ext4_label(image) != base.get("filesystem_label"):
        raise ContractError("base filesystem label mismatch")

    required = {
        "/sbin/init": (0o755, 0, 0),
        TARGETS["firstboot"]: (0o755, 0, 0),
        "/usr/local/sbin/a90-d3-return-supervisor-v3405": (0o755, 0, 0),
        "/usr/local/sbin/a90-debian-display-v1": (0o755, 0, 0),
        "/usr/local/sbin/a90-debian-display-launcher-v1": (0o755, 0, 0),
        TARGETS["inittab"]: (0o644, 0, 0),
        TARGETS["stage"]: (0o644, 0, 0),
    }
    for target, expected in required.items():
        metadata = phase2.debugfs_stat(image, target)
        if metadata is None:
            raise ContractError(f"base image lacks {target}")
        actual = (metadata["mode"], metadata["uid"], metadata["gid"])
        if actual != expected:
            raise ContractError(
                f"base metadata changed for {target}: got {actual}, expected {expected}"
            )
    content_pins = {
        TARGETS["firstboot"]: base["firstboot_sha256"],
        "/usr/local/sbin/a90-d3-return-supervisor-v3405": base[
            "return_supervisor_sha256"
        ],
        "/usr/local/sbin/a90-debian-display-v1": base["display_sha256"],
        "/usr/local/sbin/a90-debian-display-launcher-v1": base[
            "display_launcher_sha256"
        ],
        TARGETS["inittab"]: base["inittab_sha256"],
        TARGETS["stage"]: base["stage_sha256"],
    }
    for target, expected_value in content_pins.items():
        expected = require_sha256(expected_value, f"base {target} pin")
        if sha256_bytes(phase2.debugfs_cat(image, target)) != expected:
            raise ContractError(f"base content changed for {target}")
    if phase2.debugfs_stat(image, TARGETS["service"]) is not None:
        raise ContractError("base image already contains the Phase 3 service")
    if phase2.debugfs_stat(image, TARGETS["wifi_handoff"]) is not None:
        raise ContractError("base image already contains the Wi-Fi handoff service")
    for target in RUNTIME_ABSENT:
        if phase2.debugfs_stat(image, target) is not None:
            raise ContractError(f"base image contains runtime/private path: {target}")
    return image, receipt


def audit() -> dict[str, Any]:
    manifest, manifest_sha256 = load_manifest()
    sources = manifest["sources"]
    source_paths = {
        key: require_pinned_file(sources, key, f"{key}_sha256", key)
        for key in (
            "firstboot",
            "service",
            "wifi_handoff",
            "resolver_mountpoint",
            "inittab",
            "stage",
            "builder",
            "phase2_builder",
            "return_builder",
            "return_supervisor_source",
        )
    }
    issues = [
        *validate_firstboot(source_paths["firstboot"].read_text(encoding="utf-8")),
        *validate_service(source_paths["service"].read_text(encoding="utf-8")),
        *validate_wifi_handoff(
            source_paths["wifi_handoff"].read_text(encoding="utf-8")
        ),
        *validate_inittab(source_paths["inittab"].read_text(encoding="utf-8")),
        *validate_stage(source_paths["stage"].read_text(encoding="utf-8")),
    ]
    if issues:
        raise ContractError("; ".join(issues))
    base_image, base_receipt = validate_base(manifest)
    return {
        "manifest": manifest,
        "manifest_sha256": manifest_sha256,
        "sources": source_paths,
        "source_sha256": {
            key: sha256_file(path) for key, path in source_paths.items()
        },
        "base_image": base_image,
        "base_receipt": base_receipt,
        "tool_versions": validate_tools(),
    }


def output_root(requested: Path) -> Path:
    resolved = requested.resolve()
    try:
        relative = resolved.relative_to(PRIVATE_OUTPUTS.resolve())
    except ValueError as error:
        raise ContractError(
            f"output must stay under {PRIVATE_OUTPUTS.resolve()}"
        ) from error
    if not relative.parts:
        raise ContractError("output cannot be the private output root")
    if resolved.exists() or resolved.is_symlink():
        raise FileExistsError(f"absent-only output exists: {resolved}")
    return resolved


def normalize_ext4_metadata(image: Path) -> None:
    for target in ("/etc", "/usr/local/sbin"):
        for field in ("atime", "ctime", "mtime", "crtime"):
            phase2.debugfs(
                image,
                f"set_inode_field {target} {field} 0",
                writable=True,
            )
    commands = "\n".join(
        (
            "set_current_time 1",
            f"set_super_value volume_name {FILESYSTEM_LABEL}",
            "set_super_value mtime 0",
            "set_super_value lastcheck 0",
            "",
        )
    ).encode("ascii")
    phase2.run(
        ["debugfs", "-w", image],
        timeout=60.0,
        input_bytes=commands,
    )


def build_image(state: dict[str, Any], root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, mode=0o700)
    overlay = root / "overlay"
    overlay.mkdir(mode=0o700)
    overlay_paths: dict[str, Path] = {}
    for key in (
        "firstboot",
        "service",
        "wifi_handoff",
        "resolver_mountpoint",
        "inittab",
        "stage",
    ):
        target = overlay / Path(TARGETS[key]).name
        shutil.copyfile(state["sources"][key], target)
        target.chmod(
            0o700 if key in {"firstboot", "service", "wifi_handoff"} else 0o600
        )
        overlay_paths[key] = target

    image = root / "phase3-network-ssh-v1.img"
    phase2.run(
        [
            "cp",
            "--reflink=auto",
            "--sparse=always",
            state["base_image"],
            image,
        ],
        timeout=300.0,
    )
    image.chmod(0o600)
    base_sha = state["manifest"]["base"]["image_sha256"]
    if sha256_file(image) != base_sha:
        raise ContractError("pre-overlay clone differs from the pinned base")
    overlays = [
        phase2.replace_ext4_file(
            image,
            overlay_paths[key],
            TARGETS[key],
            mode=0o755 if key in {"firstboot", "service", "wifi_handoff"} else 0o644,
        )
        for key in (
            "firstboot",
            "service",
            "wifi_handoff",
            "resolver_mountpoint",
            "inittab",
            "stage",
        )
    ]
    normalize_ext4_metadata(image)
    fsck = phase2.run(["e2fsck", "-fn", image], timeout=300.0, check=False)
    if fsck.returncode != 0:
        detail = (fsck.stdout + fsck.stderr).decode(
            "utf-8", errors="replace"
        )[-2000:]
        raise ContractError(f"read-only e2fsck failed: {detail}")
    if image.stat().st_size != IMAGE_BYTES:
        raise ContractError("output image size changed")
    if read_ext4_label(image) != FILESYSTEM_LABEL:
        raise ContractError("output filesystem label mismatch")
    for key in (
        "firstboot",
        "service",
        "wifi_handoff",
        "resolver_mountpoint",
        "inittab",
        "stage",
    ):
        expected = sha256_file(state["sources"][key])
        actual = sha256_bytes(phase2.debugfs_cat(image, TARGETS[key]))
        if actual != expected:
            raise ContractError(f"output content mismatch for {TARGETS[key]}")
    for target, expected in (
        (
            "/usr/local/sbin/a90-d3-return-supervisor-v3405",
            state["manifest"]["base"]["return_supervisor_sha256"],
        ),
        (
            "/usr/local/sbin/a90-debian-display-v1",
            state["manifest"]["base"]["display_sha256"],
        ),
        (
            "/usr/local/sbin/a90-debian-display-launcher-v1",
            state["manifest"]["base"]["display_launcher_sha256"],
        ),
    ):
        if sha256_bytes(phase2.debugfs_cat(image, target)) != expected:
            raise ContractError(f"output changed retained component: {target}")
    for target in RUNTIME_ABSENT:
        if phase2.debugfs_stat(image, target) is not None:
            raise ContractError(f"output contains runtime/private path: {target}")
    return {
        "image": {
            "path": image,
            "sha256": sha256_file(image),
            "bytes": image.stat().st_size,
            "label": FILESYSTEM_LABEL,
        },
        "overlays": overlays,
        "e2fsck_read_only_rc": fsck.returncode,
    }


def serializable(value: dict[str, Any], root: Path) -> dict[str, Any]:
    return json.loads(
        json.dumps(
            value,
            default=lambda item: str(item.relative_to(root)),
        )
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def build_ab(requested: Path) -> dict[str, Any]:
    root = output_root(requested)
    state = audit()
    base_before = sha256_file(state["base_image"])
    root.mkdir(parents=True, mode=0o700)
    build_a = build_image(state, root / "A")
    build_b = build_image(state, root / "B")
    image_identical = filecmp.cmp(
        root / "A/phase3-network-ssh-v1.img",
        root / "B/phase3-network-ssh-v1.img",
        shallow=False,
    )
    source_unchanged = all(
        sha256_file(state["sources"][key]) == digest
        for key, digest in state["source_sha256"].items()
    )
    base_unchanged = sha256_file(state["base_image"]) == base_before
    receipt = {
        "schema": "a90-phase3-network-ssh-v1-ab-receipt",
        "profile": PROFILE,
        "candidate_authority": False,
        "timestamp_utc": (
            dt.datetime.now(dt.UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "manifest_sha256": state["manifest_sha256"],
        "source_sha256": state["source_sha256"],
        "base": {
            "image_sha256": state["manifest"]["base"]["image_sha256"],
            "receipt_sha256": state["manifest"]["base"]["receipt_sha256"],
            "unchanged": base_unchanged,
        },
        "tool_versions": state["tool_versions"],
        "A": serializable(build_a, root),
        "B": serializable(build_b, root),
        "image_byte_identical": image_identical,
        "source_unchanged": source_unchanged,
        "host_only": True,
        "device_action": False,
        "flash": False,
    }
    write_json(root / "ab-receipt.json", receipt)
    if not all((image_identical, source_unchanged, base_unchanged)):
        raise ContractError("A/B or immutable-input closure failed")
    return receipt


def audit_payload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "candidate_authority": False,
        "manifest_sha256": state["manifest_sha256"],
        "source_sha256": state["source_sha256"],
        "base_image_sha256": state["manifest"]["base"]["image_sha256"],
        "base_receipt_sha256": state["manifest"]["base"]["receipt_sha256"],
        "tool_versions": state["tool_versions"],
        "host_only": True,
        "device_action": False,
        "flash": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    outputs = parser.add_mutually_exclusive_group(required=True)
    outputs.add_argument("--audit-only", action="store_true")
    outputs.add_argument("--ab-root", type=Path)
    args = parser.parse_args(argv)
    os.environ.update({"LC_ALL": "C", "LANG": "C", "TZ": "UTC"})
    if args.audit_only:
        print(json.dumps(audit_payload(audit()), indent=2, sort_keys=True))
        return 0
    assert args.ab_root is not None
    print(json.dumps(build_ab(args.ab_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
