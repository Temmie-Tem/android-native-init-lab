#!/usr/bin/env python3
"""Prepare a fresh V3405 D3 return-diagnostic ext4 image.

This host-only builder clones the already package-authenticated clean D3 ext4
image so its Debian inode ownership is preserved, adds the static V3405 return
supervisor, and replaces only the firstboot/stage files. It does not contact a
device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
PRIVATE_ROOT = REPO_ROOT / "workspace" / "private"
DEFAULT_BASE_IMAGE = (
    PRIVATE_ROOT
    / "builds"
    / "server-distro"
    / "a90-v3403-d3-immutable-source-20260730.img"
)
BASE_SUMMARY = (
    PRIVATE_ROOT
    / "builds"
    / "server-distro"
    / "a90-v3403-d3-immutable-source-20260730-summary.json"
)
EXPECTED_BASE_SUMMARY_SHA256 = (
    "6d78cbd773b52e1216cbdfe8b8dc127b0d0a05866300511ff4c086ebf488b8f6"
)
EXPECTED_BASE_IMAGE_SHA256 = (
    "16c504a8b1860fcc56272140b48d27a015bab1748b6c6be10fdb958bcdd7d749"
)
DEFAULT_OUT_DIR = PRIVATE_ROOT / "builds" / "server-distro"
SUPERVISOR_SOURCE = SCRIPT_DIR / "a90_d3_return_supervisor_v3405.c"
SUPERVISOR_TARGET = Path("usr/local/sbin/a90-d3-return-supervisor-v3405")
FIRSTBOOT_TARGET = Path("etc/a90-d3-firstboot")
STAGE_TARGET = Path("etc/a90-server-distro-stage")
DEFAULT_IMAGE_SIZE = "2G"
DEFAULT_DELAY_SEC = 120
DEFAULT_GRACE_SEC = 20
DEFAULT_NCM_IP = "192.168.7.2"
DEFAULT_NCM_PEER = "192.168.7.1"
PASS_DECISION = "a90-d3-v3405-return-diagnostic-host-pass"
RUN_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,95}\Z")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strip_c_comments(text: str) -> str:
    """Remove C comments without treating comment markers in literals as syntax."""

    output: list[str] = []
    index = 0
    state = "code"
    while index < len(text):
        current = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if current == "/" and following == "*":
                output.extend((" ", " "))
                state = "block"
                index += 2
                continue
            if current == "/" and following == "/":
                output.extend((" ", " "))
                state = "line"
                index += 2
                continue
            output.append(current)
            if current == '"':
                state = "string"
            elif current == "'":
                state = "char"
        elif state == "line":
            output.append("\n" if current == "\n" else " ")
            if current == "\n":
                state = "code"
        elif state == "block":
            output.append("\n" if current == "\n" else " ")
            if current == "*" and following == "/":
                output.append(" ")
                state = "code"
                index += 2
                continue
        else:
            output.append(current)
            if current == "\\" and following:
                output.append(following)
                index += 2
                continue
            if (state == "string" and current == '"') or (
                state == "char" and current == "'"
            ):
                state = "code"
        index += 1
    if state == "block":
        raise RuntimeError("unterminated C block comment")
    return "".join(output)


def c_function_body(text: str, name: str) -> str | None:
    match = re.search(rf"\b{name}\s*\([^;]*?\)\s*\{{", text, flags=re.DOTALL)
    if match is None:
        return None
    opening = text.find("{", match.start())
    depth = 0
    state = "code"
    index = opening
    while index < len(text):
        current = text[index]
        if state == "code":
            if current == '"':
                state = "string"
            elif current == "'":
                state = "char"
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    return text[opening + 1 : index]
        else:
            if current == "\\":
                index += 1
            elif (state == "string" and current == '"') or (
                state == "char" and current == "'"
            ):
                state = "code"
        index += 1
    return None


def run(command: list[str], *, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_bytes(
    command: list[str], *, timeout: float = 120.0
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        timeout=timeout,
    )


def debugfs_text(image: Path, command: str, *, writable: bool = False) -> str:
    invocation = ["debugfs"]
    if writable:
        invocation.append("-w")
    invocation.extend(("-R", command, str(image)))
    result = run(invocation, timeout=60.0)
    return result.stdout


def debugfs_bytes(image: Path, command: str) -> bytes:
    return run_bytes(
        ["debugfs", "-R", command, str(image)],
        timeout=60.0,
    ).stdout


def debugfs_stat(image: Path, target: str) -> dict[str, int] | None:
    text = debugfs_text(image, f"stat {target}")
    if "Inode:" not in text:
        return None
    mode_match = re.search(r"\bMode:\s+0([0-7]{3,4})\b", text)
    owner_match = re.search(r"\bUser:\s+(\d+)\s+Group:\s+(\d+)\b", text)
    size_match = re.search(r"\bSize:\s+(\d+)\b", text)
    if mode_match is None or owner_match is None or size_match is None:
        raise RuntimeError(f"could not parse debugfs stat for {target}")
    return {
        "mode": int(mode_match.group(1), 8),
        "uid": int(owner_match.group(1)),
        "gid": int(owner_match.group(2)),
        "size": int(size_match.group(1)),
    }


def write_json(path: Path, payload: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(0o600)
    temporary.replace(path)


def require_tools(cc: str) -> None:
    for tool in (cc, "cp", "debugfs", "e2fsck", "file", "tune2fs"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"missing required host tool: {tool}")


def validate_network_config(ncm_ip: str, ncm_peer: str, ssh_port: int) -> None:
    try:
        local = ipaddress.IPv4Address(ncm_ip)
        peer = ipaddress.IPv4Address(ncm_peer)
    except ipaddress.AddressValueError as error:
        raise RuntimeError(f"invalid canonical IPv4 configuration: {error}") from error
    if str(local) != ncm_ip or str(peer) != ncm_peer:
        raise RuntimeError("NCM addresses must use canonical dotted-quad form")
    network = ipaddress.IPv4Network(f"{local}/24", strict=False)
    if local not in network.hosts() or peer not in network.hosts():
        raise RuntimeError("NCM addresses must be usable /24 host addresses")
    if peer not in network or local == peer:
        raise RuntimeError("NCM peer must be distinct and within the local /24")
    if not isinstance(ssh_port, int) or isinstance(ssh_port, bool):
        raise RuntimeError("ssh-port must be an integer")
    if not 1 <= ssh_port <= 65535:
        raise RuntimeError("ssh-port must be in 1..65535")


def validate_timing(delay_sec: int, grace_sec: int) -> None:
    if (
        not isinstance(delay_sec, int)
        or isinstance(delay_sec, bool)
        or not 1 <= delay_sec <= 600
    ):
        raise RuntimeError("delay-sec must be an integer in 1..600")
    if (
        not isinstance(grace_sec, int)
        or isinstance(grace_sec, bool)
        or not 1 <= grace_sec <= 60
    ):
        raise RuntimeError("grace-sec must be an integer in 1..60")


def firstboot_script(
    ncm_ip: str,
    ncm_peer: str,
    ssh_port: int,
    delay_sec: int,
    grace_sec: int,
) -> str:
    validate_network_config(ncm_ip, ncm_peer, ssh_port)
    validate_timing(delay_sec, grace_sec)
    return f"""#!/bin/sh
set +e
PATH=/usr/sbin:/usr/bin:/sbin:/bin

RETURN_SUPERVISOR=/{SUPERVISOR_TARGET}
RETURN_SUPERVISOR_PID=$("$RETURN_SUPERVISOR" --arm {delay_sec} {grace_sec})
RETURN_SUPERVISOR_RC=$?
if [ "$RETURN_SUPERVISOR_RC" -ne 0 ]; then
  exit 71
fi
case "$RETURN_SUPERVISOR_PID" in
  ''|*[!0-9]*) exit 72 ;;
esac

mkdir -p /run /tmp /root/.ssh /etc/dropbear
echo "$RETURN_SUPERVISOR_PID" > /run/a90-d3-return-supervisor.pid
chmod 700 /root/.ssh 2>/dev/null || true
IP=/usr/bin/ip
[ -x "$IP" ] || IP=/bin/ip

$IP link set ncm0 up >/dev/null 2>&1 || true
$IP addr replace {ncm_ip}/24 dev ncm0 >/dev/null 2>&1 || true
$IP route replace {ncm_peer} dev ncm0 >/dev/null 2>&1 || true

{{
  echo A90D3_MARKER
  echo stage=D3-v3405-return-diagnostic
  echo debian_version=$(cat /etc/debian_version 2>/dev/null)
  echo pid1_comm=$(cat /proc/1/comm 2>/dev/null)
  echo proc1_exe=$(readlink /proc/1/exe 2>/dev/null)
  echo ncm_ip={ncm_ip}
  echo return_supervisor_pid="$RETURN_SUPERVISOR_PID"
  echo return_delay_sec={delay_sec}
  echo sync_grace_sec={grace_sec}
  echo recovery_action=sysrq-b-only
  test -f /etc/a90-server-distro-stage && cat /etc/a90-server-distro-stage
}} > /run/a90-d3-marker

if [ ! -s /etc/dropbear/dropbear_ed25519_host_key ]; then
  /usr/bin/dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key >/run/a90-d3-dropbearkey.log 2>&1
fi

if [ -s /root/.ssh/authorized_keys ]; then
  /usr/sbin/dropbear -E -r /etc/dropbear/dropbear_ed25519_host_key \\
    -p {ncm_ip}:{ssh_port} -P /run/a90-d3-dropbear.pid -s -j -k \\
    >>/run/a90-d3-dropbear.log 2>&1
  echo dropbear_started=1 >> /run/a90-d3-marker
else
  echo dropbear_started=0 >> /run/a90-d3-marker
fi

exit 0
"""


def validate_firstboot(
    text: str,
    *,
    delay_sec: int = DEFAULT_DELAY_SEC,
    grace_sec: int = DEFAULT_GRACE_SEC,
) -> tuple[str, ...]:
    issues: list[str] = []
    required = (
        f"RETURN_SUPERVISOR=/{SUPERVISOR_TARGET}",
        f"--arm {delay_sec} {grace_sec}",
        "RETURN_SUPERVISOR_RC=$?",
        "return_supervisor_pid=",
        "recovery_action=sysrq-b-only",
        "$IP addr replace",
        "/usr/sbin/dropbear",
    )
    for token in required:
        if token not in text:
            issues.append(f"missing firstboot token: {token}")
    supervisor_pos = text.find("RETURN_SUPERVISOR_PID=$(")
    for later in ("mkdir -p", "$IP addr replace", "A90D3_MARKER", "/usr/sbin/dropbear"):
        position = text.find(later)
        if supervisor_pos < 0 or position < 0 or supervisor_pos >= position:
            issues.append(f"supervisor is not armed before: {later}")
    for forbidden in (
        "\n  sync\n",
        "\nsync\n",
        "/sbin/reboot",
        "/proc/sysrq-trigger",
    ):
        if forbidden in text:
            issues.append(f"forbidden firstboot recovery token: {forbidden!r}")
    return tuple(issues)


def validate_supervisor_source(text: str) -> tuple[str, ...]:
    issues: list[str] = []
    try:
        source = strip_c_comments(text)
    except RuntimeError as error:
        return (str(error),)
    required = (
        '#define A90_SYSRQ_PATH "/proc/sysrq-trigger"',
        '#define A90_PMSG_PATH "/dev/pmsg0"',
        "preopen_interfaces(&io)",
        "mlockall(MCL_CURRENT | MCL_FUTURE)",
        "sync();",
        '"/proc/%ld/stat"',
        '"/proc/%ld/wchan"',
        "state_from_stat(stat_text)",
        'write_all(io->sysrq_fd, "b\\n", 2U)',
        'write_all(sysrq_fd, "b\\n", 2U)',
        "reboot(LINUX_REBOOT_CMD_RESTART)",
        "request_reboot_bounded(&io)",
    )
    for token in required:
        if token not in source:
            issues.append(f"missing supervisor token: {token}")
    for forbidden in (
        '"s\\n"',
        "syncfs(",
        "fsync(",
        "fdatasync(",
        "execve(",
        "execl(",
        "execvp(",
        "system(",
        "popen(",
        "/sbin/reboot",
        "LINUX_REBOOT_CMD_RESTART2",
    ):
        if forbidden in source:
            issues.append(f"forbidden supervisor token: {forbidden}")
    if source.count("sync();") != 1:
        issues.append("global sync must exist exactly once in diagnostic child")
    trigger_body = c_function_body(source, "trigger_b_only")
    arm_trigger_body = c_function_body(source, "arm_parent_b_only")
    evidence_body = c_function_body(source, "evidence_child")
    evidence_parent_body = c_function_body(source, "collect_evidence_then_b")
    reboot_body = c_function_body(source, "reboot_child")
    reboot_parent_body = c_function_body(source, "request_reboot_bounded")
    sync_body = c_function_body(source, "sync_child")
    bodies = {
        "trigger_b_only": trigger_body,
        "arm_parent_b_only": arm_trigger_body,
        "evidence_child": evidence_body,
        "collect_evidence_then_b": evidence_parent_body,
        "reboot_child": reboot_body,
        "request_reboot_bounded": reboot_parent_body,
        "sync_child": sync_body,
    }
    for name, body in bodies.items():
        if body is None:
            issues.append(f"missing or malformed supervisor function: {name}")
    if trigger_body is not None:
        if trigger_body.count('write_all(io->sysrq_fd, "b\\n", 2U)') != 1:
            issues.append("trigger_b_only must contain one exact b-only write")
        if any(token in trigger_body for token in ("emit_marker(", "open(", "read(")):
            issues.append("trigger_b_only must not perform late evidence I/O")
    if arm_trigger_body is not None and arm_trigger_body.count(
        'write_all(sysrq_fd, "b\\n", 2U)'
    ) != 1:
        issues.append("arm_parent_b_only must contain one exact b-only write")
    if sync_body is not None and sync_body.count("sync();") != 1:
        issues.append("sync() must be isolated in sync_child")
    if evidence_body is not None:
        for token in ("read_sync_evidence(", "phase=sync-timeout"):
            if token not in evidence_body:
                issues.append(f"evidence_child is missing: {token}")
    if evidence_parent_body is not None:
        for token in (
            "evidence_pid = fork()",
            "wait_child_until(evidence_pid",
            'trigger_b_only(io, "sync-timeout")',
        ):
            if token not in evidence_parent_body:
                issues.append(f"bounded evidence parent is missing: {token}")
        if "read_sync_evidence(" in evidence_parent_body or "emit_marker(" in evidence_parent_body:
            issues.append("evidence parent must not perform late evidence I/O")
    if reboot_body is not None and reboot_body.count(
        "reboot(LINUX_REBOOT_CMD_RESTART)"
    ) != 1:
        issues.append("reboot syscall must exist exactly once in reboot_child")
    if reboot_parent_body is not None:
        for token in (
            "reboot_pid = fork()",
            "wait_child_until(reboot_pid",
            'trigger_b_only(io, "reboot-return-or-timeout")',
        ):
            if token not in reboot_parent_body:
                issues.append(f"bounded reboot parent is missing: {token}")
        if "reboot(LINUX_REBOOT_CMD_RESTART)" in reboot_parent_body:
            issues.append("reboot parent must not call the reboot syscall")
    ordered = (
        "preopen_interfaces(&io)",
        "mlockall(MCL_CURRENT | MCL_FUTURE)",
        "phase=armed",
    )
    positions = tuple(source.find(token) for token in ordered)
    if any(position < 0 for position in positions) or positions != tuple(
        sorted(positions)
    ):
        issues.append("preopen/mlock/armed order is not closed")
    return tuple(issues)


def validate_base_provenance(base_image: Path) -> tuple[str, ...]:
    issues: list[str] = []
    if not base_image.is_absolute() or base_image != DEFAULT_BASE_IMAGE:
        issues.append("base image must use the exact pinned absolute pathname")
        return tuple(issues)
    if base_image.is_symlink():
        issues.append("pinned base image pathname must not be a symlink")
        return tuple(issues)
    resolved = base_image.resolve()
    if resolved != DEFAULT_BASE_IMAGE.resolve():
        issues.append("base image must be the exact pinned V3403 clean ext4")
        return tuple(issues)
    if not resolved.is_file() or resolved.is_symlink():
        issues.append("pinned base image must be a regular non-symlink file")
        return tuple(issues)
    if resolved.stat().st_size != 2147483648:
        issues.append("pinned base image size is not exactly 2 GiB")
        return tuple(issues)
    base_sha = sha256_file(resolved)
    if base_sha != EXPECTED_BASE_IMAGE_SHA256:
        issues.append(
            f"base image hash mismatch: expected {EXPECTED_BASE_IMAGE_SHA256}, "
            f"got {base_sha}"
        )
        return tuple(issues)
    if not BASE_SUMMARY.is_file() or BASE_SUMMARY.is_symlink():
        issues.append(f"pinned base summary is absent: {BASE_SUMMARY}")
        return tuple(issues)
    summary_sha = sha256_file(BASE_SUMMARY)
    if summary_sha != EXPECTED_BASE_SUMMARY_SHA256:
        issues.append(
            f"base summary hash mismatch: expected {EXPECTED_BASE_SUMMARY_SHA256}, "
            f"got {summary_sha}"
        )
        return tuple(issues)
    try:
        summary = json.loads(BASE_SUMMARY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        issues.append(f"base summary is unreadable: {error}")
        return tuple(issues)
    if summary.get("decision") != "server-distro-d3a-sysvinit-rootfs-host-pass":
        issues.append("base summary decision is not the accepted host-pass value")
    if (REPO_ROOT / str(summary.get("image", ""))).resolve() != resolved:
        issues.append("base summary image path does not bind the selected image")
    if summary.get("image_sha256") != EXPECTED_BASE_IMAGE_SHA256:
        issues.append("base summary clean-image identity is not the pinned value")
    required_stats = {
        "/sbin/init": (0o755, 0, 0),
        "/etc/inittab": (0o644, 0, 0),
        "/etc/a90-d3-firstboot": (0o755, 0, 0),
        "/usr/sbin/dropbear": (0o755, 0, 0),
        "/usr/bin/dropbearkey": (0o755, 0, 0),
        "/usr/local/sbin": (0o755, 0, 0),
        "/root": (0o700, 0, 0),
    }
    for target, expected in required_stats.items():
        metadata = debugfs_stat(resolved, target)
        if metadata is None:
            issues.append(f"base image is missing required path: {target}")
            continue
        actual = (metadata["mode"], metadata["uid"], metadata["gid"])
        if actual != expected:
            issues.append(
                f"base image metadata mismatch for {target}: "
                f"expected {expected}, got {actual}"
            )
    absent_paths = (
        "/usr/local/sbin/a90-d3-return-supervisor-v3405",
        "/run/a90-d3-autoreboot.pid",
        "/run/a90-d3-return-supervisor.pid",
        "/run/a90-d3-marker",
        "/run/a90-d3-dropbear.pid",
        "/etc/dropbear/dropbear_ed25519_host_key",
        "/root/.ssh/authorized_keys",
        "/etc/wpa_supplicant/wpa_supplicant.conf",
        "/etc/a90-wifi-sta.conf",
    )
    for target in absent_paths:
        if debugfs_stat(resolved, target) is not None:
            issues.append(f"base image contains forbidden runtime/credential path: {target}")
    return tuple(issues)


def build_supervisor(cc: str, output: Path) -> dict[str, Any]:
    command = [
        cc,
        "-static",
        "-Os",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-fno-strict-aliasing",
        str(SUPERVISOR_SOURCE),
        "-o",
        str(output),
    ]
    run(command)
    output.chmod(0o700)
    file_output = run(["file", str(output)]).stdout.strip()
    if (
        "ELF 64-bit LSB executable, ARM aarch64" not in file_output
        or "statically linked" not in file_output
    ):
        raise RuntimeError(f"unexpected supervisor output: {file_output}")
    return {
        "path": rel(output),
        "sha256": sha256_file(output),
        "size": output.stat().st_size,
        "file": file_output,
        "command": command,
    }


def install_contract(
    rootfs: Path,
    helper: Path,
    *,
    ncm_ip: str,
    ncm_peer: str,
    ssh_port: int,
    delay_sec: int,
    grace_sec: int,
) -> dict[str, Any]:
    helper_target = rootfs / SUPERVISOR_TARGET
    helper_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(helper, helper_target)
    helper_target.chmod(0o755)

    firstboot_text = firstboot_script(
        ncm_ip,
        ncm_peer,
        ssh_port,
        delay_sec,
        grace_sec,
    )
    issues = validate_firstboot(
        firstboot_text,
        delay_sec=delay_sec,
        grace_sec=grace_sec,
    )
    if issues:
        raise RuntimeError("; ".join(issues))
    firstboot = rootfs / FIRSTBOOT_TARGET
    firstboot.parent.mkdir(parents=True, exist_ok=True)
    firstboot.write_text(firstboot_text, encoding="utf-8")
    firstboot.chmod(0o755)

    stage = rootfs / STAGE_TARGET
    stage.parent.mkdir(parents=True, exist_ok=True)
    stage.write_text(
        "\n".join(
            (
                "stage=D3 V3405 return diagnostic",
                "purpose=classify-global-sync-before-recovery",
                "return-supervisor=/usr/local/sbin/a90-d3-return-supervisor-v3405",
                f"return-delay-sec={delay_sec}",
                f"sync-grace-sec={grace_sec}",
                "sysrq=preopened-b-only-no-emergency-sync",
                "marker=pmsg-preopened-positive-control-and-sync-state-wchan",
                "pmsg-retention=must-be-proven-by-this-run",
                "userdata=untouched",
                "",
            )
        ),
        encoding="utf-8",
    )
    stage.chmod(0o644)
    return {
        "helper_target": str(SUPERVISOR_TARGET),
        "helper_mode": oct(helper_target.stat().st_mode & 0o777),
        "firstboot_target": str(FIRSTBOOT_TARGET),
        "firstboot_mode": oct(firstboot.stat().st_mode & 0o777),
        "firstboot_sha256": sha256_file(firstboot),
        "stage_sha256": sha256_file(stage),
    }


def replace_ext4_file(
    image: Path,
    host_source: Path,
    target: str,
    *,
    mode: int,
) -> dict[str, Any]:
    source_text = str(host_source.resolve())
    if not host_source.is_file() or host_source.is_symlink():
        raise RuntimeError(f"overlay source must be a regular non-symlink file: {host_source}")
    if re.fullmatch(r"/[A-Za-z0-9._/-]+", source_text) is None:
        raise RuntimeError(f"overlay source path is unsafe for debugfs: {host_source}")
    if re.fullmatch(r"/[A-Za-z0-9._/-]+", target) is None or any(
        part in ("", ".", "..") for part in target.split("/")[1:]
    ):
        raise RuntimeError(f"unsafe fixed ext4 target: {target}")
    if debugfs_stat(image, target) is not None:
        debugfs_text(image, f"rm {target}", writable=True)
        if debugfs_stat(image, target) is not None:
            raise RuntimeError(f"debugfs did not remove existing target: {target}")
    debugfs_text(
        image,
        f"write {source_text} {target}",
        writable=True,
    )
    for field, value in (
        ("mode", f"0100{mode:03o}"),
        ("uid", "0"),
        ("gid", "0"),
    ):
        debugfs_text(
            image,
            f"set_inode_field {target} {field} {value}",
            writable=True,
        )
    metadata = debugfs_stat(image, target)
    if metadata is None:
        raise RuntimeError(f"debugfs target is absent after write: {target}")
    expected_metadata = {
        "mode": mode,
        "uid": 0,
        "gid": 0,
        "size": host_source.stat().st_size,
    }
    if metadata != expected_metadata:
        raise RuntimeError(
            f"debugfs target metadata mismatch for {target}: "
            f"expected {expected_metadata}, got {metadata}"
        )
    content_sha = hashlib.sha256(debugfs_bytes(image, f"cat {target}")).hexdigest()
    source_sha = sha256_file(host_source)
    if content_sha != source_sha:
        raise RuntimeError(
            f"debugfs target content mismatch for {target}: "
            f"expected {source_sha}, got {content_sha}"
        )
    return {
        "target": target,
        "mode": oct(mode),
        "uid": 0,
        "gid": 0,
        "size": metadata["size"],
        "sha256": content_sha,
    }


def clone_and_overlay_image(
    base_image: Path,
    image: Path,
    overlay: Path,
) -> dict[str, Any]:
    run(
        [
            "cp",
            "--reflink=auto",
            "--sparse=always",
            str(base_image),
            str(image),
        ],
        timeout=300.0,
    )
    image.chmod(0o600)
    cloned_sha = sha256_file(image)
    if cloned_sha != EXPECTED_BASE_IMAGE_SHA256:
        raise RuntimeError(
            f"pre-overlay clone hash mismatch: expected {EXPECTED_BASE_IMAGE_SHA256}, "
            f"got {cloned_sha}"
        )
    files = (
        replace_ext4_file(
            image,
            overlay / SUPERVISOR_TARGET,
            f"/{SUPERVISOR_TARGET}",
            mode=0o755,
        ),
        replace_ext4_file(
            image,
            overlay / FIRSTBOOT_TARGET,
            f"/{FIRSTBOOT_TARGET}",
            mode=0o755,
        ),
        replace_ext4_file(
            image,
            overlay / STAGE_TARGET,
            f"/{STAGE_TARGET}",
            mode=0o644,
        ),
    )
    run(["tune2fs", "-L", "A90D3V3405", str(image)])
    if image.stat().st_size != 2147483648:
        raise RuntimeError("overlaid image size changed from exact 2 GiB")
    tune2fs_list = run(["tune2fs", "-l", str(image)]).stdout
    if "Filesystem volume name:   A90D3V3405" not in tune2fs_list:
        raise RuntimeError("overlaid image label verification failed")
    fsck = subprocess.run(
        ["e2fsck", "-fn", str(image)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=300.0,
    )
    if fsck.returncode != 0:
        raise RuntimeError(
            f"read-only ext4 validation failed rc={fsck.returncode}: "
            f"{fsck.stdout[-2000:]} {fsck.stderr[-2000:]}"
        )
    critical_base = {
        "/sbin/init": (0o755, 0, 0),
        "/etc/inittab": (0o644, 0, 0),
        "/root": (0o700, 0, 0),
    }
    for target, expected in critical_base.items():
        metadata = debugfs_stat(image, target)
        if metadata is None:
            raise RuntimeError(f"overlaid image lost critical base path: {target}")
        actual = (metadata["mode"], metadata["uid"], metadata["gid"])
        if actual != expected:
            raise RuntimeError(
                f"overlaid image changed base metadata for {target}: "
                f"expected {expected}, got {actual}"
            )
    if sha256_file(base_image) != EXPECTED_BASE_IMAGE_SHA256:
        raise RuntimeError("pinned base image changed during overlay build")
    return {
        "base_clone_sha256": cloned_sha,
        "files": list(files),
        "e2fsck_read_only_rc": fsck.returncode,
        "e2fsck_read_only_clean": True,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    if not args.base_image.is_absolute() or args.base_image != DEFAULT_BASE_IMAGE:
        raise RuntimeError("base image must use the exact pinned absolute pathname")
    if not args.out_dir.is_absolute() or args.out_dir != DEFAULT_OUT_DIR:
        raise RuntimeError("output directory must use the exact private absolute pathname")
    args.base_image = args.base_image.resolve()
    args.out_dir = args.out_dir.resolve()
    if RUN_ID_PATTERN.fullmatch(args.run_id) is None:
        raise RuntimeError("run-id must match [a-z0-9][a-z0-9._-]{0,95}")
    if args.out_dir != DEFAULT_OUT_DIR.resolve():
        raise RuntimeError("output directory must remain the exact private server-distro root")
    if args.image_size != DEFAULT_IMAGE_SIZE:
        raise RuntimeError(f"image-size must remain exactly {DEFAULT_IMAGE_SIZE}")
    validate_network_config(args.ncm_ip, args.ncm_peer, args.ssh_port)
    validate_timing(args.delay_sec, args.grace_sec)
    if not args.base_image.is_file():
        raise RuntimeError(f"base image is absent: {args.base_image}")
    provenance_issues = validate_base_provenance(args.base_image)
    if provenance_issues:
        raise RuntimeError("; ".join(provenance_issues))
    supervisor_source_text = SUPERVISOR_SOURCE.read_text(encoding="utf-8")
    supervisor_source_sha = hashlib.sha256(
        supervisor_source_text.encode("utf-8")
    ).hexdigest()
    supervisor_issues = validate_supervisor_source(supervisor_source_text)
    if supervisor_issues:
        raise RuntimeError("; ".join(supervisor_issues))
    run_dir = (args.out_dir / args.run_id).resolve()
    if not is_under(run_dir, args.out_dir) or not is_under(run_dir, PRIVATE_ROOT):
        raise RuntimeError("resolved run directory escaped the private output root")
    overlay = run_dir / "overlay"
    image = run_dir / f"{args.run_id}.img"
    helper = run_dir / "a90-d3-return-supervisor-v3405"
    summary_path = run_dir / "summary.json"
    if run_dir.exists():
        raise FileExistsError(f"absent-only run directory exists: {run_dir}")
    require_tools(args.cc)
    run_dir.mkdir(parents=True, mode=0o700)
    run_dir.chmod(0o700)

    helper_meta = build_supervisor(args.cc, helper)
    if sha256_file(SUPERVISOR_SOURCE) != supervisor_source_sha:
        raise RuntimeError("supervisor source changed during build")
    contract = install_contract(
        overlay,
        helper,
        ncm_ip=args.ncm_ip,
        ncm_peer=args.ncm_peer,
        ssh_port=args.ssh_port,
        delay_sec=args.delay_sec,
        grace_sec=args.grace_sec,
    )
    image_overlay = clone_and_overlay_image(
        args.base_image,
        image,
        overlay,
    )

    now = dt.datetime.now(dt.UTC).replace(microsecond=0)
    summary = {
        "decision": PASS_DECISION,
        "timestamp_utc": now.isoformat().replace("+00:00", "Z"),
        "run_id": args.run_id,
        "base_image": {
            "path": rel(args.base_image),
            "size": args.base_image.stat().st_size,
            "sha256": EXPECTED_BASE_IMAGE_SHA256,
        },
        "run_dir": rel(run_dir),
        "overlay": rel(overlay),
        "image": {
            "path": rel(image),
            "size": image.stat().st_size,
            "sha256": sha256_file(image),
            "mode": oct(image.stat().st_mode & 0o777),
            "label": "A90D3V3405",
        },
        "supervisor": helper_meta,
        "supervisor_source": {
            "path": rel(SUPERVISOR_SOURCE),
            "sha256": supervisor_source_sha,
        },
        "contract": contract,
        "image_overlay": image_overlay,
        "timing": {
            "delay_sec": args.delay_sec,
            "sync_grace_sec": args.grace_sec,
        },
        "safety": {
            "host_only": True,
            "device_action": False,
            "flash": False,
            "userdata_touch": False,
            "credentials_added": False,
            "global_sync_is_diagnostic_child_only": True,
            "base_inode_ownership_preserved_by_exact_image_clone": True,
            "overlay_inode_uid_gid_verified_root": True,
            "sysrq_action": "b-only",
            "emergency_sync": False,
            "pmsg_retention_proven": False,
            "retained_armed_positive_control_required": True,
        },
        "adoption_state": (
            "host-built-not-live-adoptable-until-retained-pmsg-observer-"
            "new-f1-manifest-and-fresh-approval"
        ),
    }
    write_json(summary_path, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--base-image", type=Path, default=DEFAULT_BASE_IMAGE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--image-size", default=DEFAULT_IMAGE_SIZE)
    parser.add_argument("--delay-sec", type=int, default=DEFAULT_DELAY_SEC)
    parser.add_argument("--grace-sec", type=int, default=DEFAULT_GRACE_SEC)
    parser.add_argument("--ncm-ip", default=DEFAULT_NCM_IP)
    parser.add_argument("--ncm-peer", default=DEFAULT_NCM_PEER)
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    args = parser.parse_args(argv)

    summary = build(args)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
