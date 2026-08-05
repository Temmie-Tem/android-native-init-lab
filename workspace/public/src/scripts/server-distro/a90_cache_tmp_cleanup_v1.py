#!/usr/bin/env python3
"""One-file attended A90 cache-space reclamation with no-replay unlink."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import stat
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_transition_d1_session_v1 as resident  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402
import a90ctl  # noqa: E402
import a90_bridge  # noqa: E402
import run_d1_chroot_mvp as d1  # noqa: E402


SCHEMA = "a90-cache-tmp-cleanup-manifest-v1"
RESULT_SCHEMA = "a90-cache-tmp-cleanup-result-v1"
JOURNAL_SCHEMA = "a90-cache-tmp-cleanup-journal-v1"
JOURNAL_NAMES = (
    "0000-open.json",
    "0001-unlink-intent.json",
    "0002-unlink-result.json",
    "0003-closed.json",
)
JOURNAL_ACTIONS = (
    "open-exact-present-unused",
    "unlink-intent",
    "unlink-result",
    "closed",
)
COMMON_RECORD_KEYS = {"schema", "action"}
OPEN_RECORD_KEYS = {
    "manifest_sha256", "execution_closure", "host_preserved",
    "opening_health", "status_record", "status", "state_record", "state",
}
INTENT_RECORD_KEYS = {
    "manifest_sha256", "selected_path", "selected_sha256",
    "unlink_dispatch_count_max", "retransmit", "s22plus_command_count",
}
RESULT_RECORD_KEYS = {
    "schema", "terminal", "intent_sha256", "unlink_dispatch_count",
    "retransmit", "unlink_record", "post_state_record", "post_state",
    "post_state_error", "final_health", "final_health_error",
    "final_status_record", "final_status", "final_status_error",
    "host_preserved", "payload_transfer", "partition_write", "flash",
    "s22plus_command_count",
}
RESULT_JOURNAL_KEYS = {"result"}
CLOSED_RECORD_KEYS = {"result_sha256", "result"}
CAPABILITY = "A90_ATTENDED_CACHE_TMP_RECLAIM_V1"
EXPECTED_VERSION = "0.11.170"
EXPECTED_BUILD = "phase3-minimal-h2-two-phase-auto-benchmark"
FIXED_PATH = (
    "/cache/a90-runtime/pkg/"
    ".boot_linux_v3355_boot_write_e5_full.img.tmp.2899667.1782985070"
)
ENABLE_PATH = "/cache/a90-auto-handoff-phase3-minimal-h2.enable"
LATCH_PATH = "/cache/a90-auto-handoff-phase3-minimal-h2.done"
HOST_NCM_ADDRESS = "192.168.7.1"
DEVICE_NCM_ADDRESS = "192.168.7.2"
RECOVERY_PROFILE = (
    "attended physical Download or TWRP path followed by the exact checked V2321 rollback"
)
PRIVATE_ROOT = (REPO_ROOT / "workspace/private").resolve()
TARGET_CONTRACT = REPO_ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md"
EXECUTION_SOURCES = {
    "runner": Path(__file__).resolve(),
    "resident": Path(resident.__file__).resolve(),
    "base": Path(base.__file__).resolve(),
    "d1_transport": Path(d1.__file__).resolve(),
    "a90ctl": Path(a90ctl.__file__).resolve(),
    "a90_bridge": Path(a90_bridge.__file__).resolve(),
    "target_contract": TARGET_CONTRACT.resolve(),
}
STATUS_RE = re.compile(
    r"^A90AUTO_STATUS binding=1 enable=(?P<enable>[01]) latch=(?P<latch>[01]) "
    r"build=phase3-minimal-h2-two-phase-auto-benchmark\r?$",
    re.MULTILINE,
)
STATE_RE = re.compile(
    r"^A90CACHE_TMP state=(?P<state>present|absent) "
    r"available_kib=(?P<available>[0-9]+) inodes_available=(?P<inodes>[0-9]+) "
    r"enable=(?P<enable>[01]) latch=(?P<latch>[01])"
    r"(?: meta=(?P<meta>[^\r\n]+) sha256=(?P<sha>[0-9a-f]{64}) "
    r"mount=(?P<mount>[0-9]+) loop=(?P<loop>[0-9]+) open=(?P<open>[0-9]+))?\r?$",
    re.MULTILINE,
)


class ContractError(RuntimeError):
    """Raised before selection widening, retransmit, or unsafe classification."""


@dataclass(frozen=True)
class CleanupSpec:
    manifest_sha256: str
    resident_manifest_path: Path
    resident_manifest_sha256: str
    execution_closure_sha256: str
    path: str
    size: int
    sha256: str
    mode: int
    uid: int
    gid: int
    nlink: int
    device: int
    inode: int
    blocks: int
    host_preserved_path: Path
    rollback_path: Path
    rollback_size: int
    rollback_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def execution_closure() -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for label, path in sorted(EXECUTION_SOURCES.items()):
        files[label] = {
            "path": str(path.relative_to(REPO_ROOT)),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    return {"sha256": _json_sha256(files), "files": files}


def require_execution_closure(expected: str) -> dict[str, Any]:
    closure = execution_closure()
    if not re.fullmatch(r"[0-9a-f]{64}", expected or ""):
        raise ContractError("expected execution closure is not a sha256")
    if closure["sha256"] != expected:
        raise ContractError("execution-critical closure changed")
    return closure


def _read_private_json(path: Path, expected_sha256: str) -> dict[str, Any]:
    resolved = path.resolve()
    if PRIVATE_ROOT not in resolved.parents:
        raise ContractError("manifest must remain under workspace/private")
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ContractError("manifest is not one regular non-symlink file")
    if sha256_file(resolved) != expected_sha256:
        raise ContractError("manifest sha256 changed")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError("manifest is not an object")
    return value


def load_cleanup_spec(path: Path, expected_sha256: str) -> CleanupSpec:
    value = _read_private_json(path, expected_sha256)
    if set(value) != {
        "schema", "capability", "target", "resident_manifest",
        "execution_closure_sha256", "selected_file", "host_preserved",
        "rollback", "recovery_profile", "inventory",
    }:
        raise ContractError("cleanup manifest key set changed")
    if (
        value.get("schema") != SCHEMA
        or value.get("capability") != CAPABILITY
        or value.get("target") != {
            "product": "SM-A908N",
            "device": "r3q",
            "resident_version": EXPECTED_VERSION,
            "resident_build": EXPECTED_BUILD,
        }
        or value.get("recovery_profile") != RECOVERY_PROFILE
    ):
        raise ContractError("cleanup manifest target/capability changed")
    resident_value = value.get("resident_manifest")
    selected = value.get("selected_file")
    preserved = value.get("host_preserved")
    rollback = value.get("rollback")
    inventory = value.get("inventory")
    if not all(isinstance(item, dict) for item in (
        resident_value, selected, preserved, rollback, inventory
    )):
        raise ContractError("cleanup manifest nested object changed")
    selected_expected_keys = {
        "path", "size", "sha256", "mode", "uid", "gid", "nlink",
        "device", "inode", "blocks",
    }
    if set(selected) != selected_expected_keys or selected.get("path") != FIXED_PATH:
        raise ContractError("cleanup selection is not the fixed path")
    numeric = ("size", "mode", "uid", "gid", "nlink", "device", "inode", "blocks")
    if any(type(selected.get(key)) is not int or selected[key] < 0 for key in numeric):
        raise ContractError("cleanup selection numeric binding changed")
    if (
        selected["size"] <= 0
        or selected["mode"] != 0o644
        or selected["uid"] != 0
        or selected["gid"] != 0
        or selected["nlink"] != 1
        or selected["blocks"] <= 0
        or not re.fullmatch(r"[0-9a-f]{64}", str(selected.get("sha256") or ""))
    ):
        raise ContractError("cleanup selection identity is not exact")
    if set(preserved) != {"path", "size", "sha256", "mode"}:
        raise ContractError("host preservation binding changed")
    preserved_path = Path(str(preserved.get("path") or "")).resolve()
    if (
        PRIVATE_ROOT not in preserved_path.parents
        or preserved.get("size") != selected["size"]
        or preserved.get("sha256") != selected["sha256"]
        or preserved.get("mode") != 0o600
    ):
        raise ContractError("host preservation is not the exact selected bytes")
    if set(resident_value) != {"path", "sha256"}:
        raise ContractError("resident manifest binding changed")
    resident_path = Path(str(resident_value.get("path") or "")).resolve()
    if (
        PRIVATE_ROOT not in resident_path.parents
        or re.fullmatch(r"[0-9a-f]{64}", str(resident_value.get("sha256") or "")) is None
    ):
        raise ContractError("resident manifest path escaped private workspace")
    if set(rollback) != {"path", "size", "sha256"}:
        raise ContractError("rollback binding changed")
    rollback_path = Path(str(rollback.get("path") or "")).resolve()
    if (
        PRIVATE_ROOT not in rollback_path.parents
        or type(rollback.get("size")) is not int
        or rollback["size"] <= 0
        or re.fullmatch(r"[0-9a-f]{64}", str(rollback.get("sha256") or "")) is None
        or re.fullmatch(
            r"[0-9a-f]{64}",
            str(value.get("execution_closure_sha256") or ""),
        ) is None
    ):
        raise ContractError("rollback or execution closure binding changed")
    if set(inventory) != {
        "captured_utc", "sequence", "cache_available_kib", "cache_inodes_available",
        "enable_absent", "latch_absent", "mount_hits", "loop_hits", "open_hits",
    }:
        raise ContractError("inventory binding changed")
    if (
        inventory.get("cache_available_kib") != 0
        or type(inventory.get("cache_inodes_available")) is not int
        or inventory["cache_inodes_available"] <= 0
        or inventory.get("enable_absent") is not True
        or inventory.get("latch_absent") is not True
        or inventory.get("mount_hits") != 0
        or inventory.get("loop_hits") != 0
        or inventory.get("open_hits") != 0
    ):
        raise ContractError("inventory does not bind the reviewed full-cache hazard")
    return CleanupSpec(
        manifest_sha256=expected_sha256,
        resident_manifest_path=resident_path,
        resident_manifest_sha256=str(resident_value["sha256"]),
        execution_closure_sha256=str(value["execution_closure_sha256"]),
        path=FIXED_PATH,
        size=selected["size"],
        sha256=selected["sha256"],
        mode=selected["mode"],
        uid=selected["uid"],
        gid=selected["gid"],
        nlink=selected["nlink"],
        device=selected["device"],
        inode=selected["inode"],
        blocks=selected["blocks"],
        host_preserved_path=preserved_path,
        rollback_path=rollback_path,
        rollback_size=int(rollback["size"]),
        rollback_sha256=str(rollback["sha256"]),
    )


def validate_resident_binding(
    cleanup: CleanupSpec,
    resident_manifest: Path,
    resident_manifest_sha256: str,
) -> resident.SessionSpec:
    if (
        resident_manifest.resolve() != cleanup.resident_manifest_path
        or resident_manifest_sha256 != cleanup.resident_manifest_sha256
    ):
        raise ContractError("live resident manifest differs from cleanup binding")
    spec = resident.load_spec(resident_manifest, resident_manifest_sha256)
    if (
        spec.candidate_version != EXPECTED_VERSION
        or spec.candidate_build != EXPECTED_BUILD
        or spec.rollback.path != cleanup.rollback_path
        or spec.rollback.size != cleanup.rollback_size
        or spec.rollback.sha256 != cleanup.rollback_sha256
        or spec.recovery_profile != RECOVERY_PROFILE
    ):
        raise ContractError("resident rollback/recovery binding changed")
    return spec


def _effect_args(timeout: float = 120.0) -> argparse.Namespace:
    return SimpleNamespace(
        bridge_host="127.0.0.1",
        bridge_port=a90ctl.DEFAULT_PORT,
        remote_timeout=timeout,
    )


def _command_receipt(args: argparse.Namespace, command: list[str], label: str) -> dict[str, Any]:
    return base.require_exact_f1_command_receipt(
        base.run_f1_cmd(args, command),
        command,
        label,
    )


def read_auto_status(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, int]]:
    command = ["auto-handoff-status"]
    receipt = _command_receipt(args, command, "cache cleanup H2 status")
    return receipt, parse_auto_status_receipt(receipt, "cache cleanup H2 status")


def parse_auto_status_receipt(receipt: Any, label: str) -> dict[str, int]:
    exact = base.require_exact_f1_command_receipt(
        receipt,
        ["auto-handoff-status"],
        label,
    )
    matches = list(STATUS_RE.finditer(str(exact.get("text") or "")))
    if len(matches) != 1:
        raise ContractError("cache cleanup H2 status is not unique")
    return {
        "enable": int(matches[0].group("enable"), 10),
        "latch": int(matches[0].group("latch"), 10),
    }


def _state_script(require_present: bool | None) -> str:
    present = "1" if require_present is True else "0" if require_present is False else "x"
    return (
        'set -eu;P="$1";S="$2";META="$3";WANT="$4";'
        'E=/cache/a90-auto-handoff-phase3-minimal-h2.enable;'
        'L=/cache/a90-auto-handoff-phase3-minimal-h2.done;'
        'A=$(/bin/busybox df -k /cache|/bin/busybox tail -n 1|'
        '/bin/busybox awk "{print \\$4}");'
        'I=$(/bin/busybox df -i /cache|/bin/busybox tail -n 1|'
        '/bin/busybox awk "{print \\$4}");'
        'if [ -e "$E" ]||[ -L "$E" ];then e=1;else e=0;fi;'
        'if [ -e "$L" ]||[ -L "$L" ];then l=1;else l=0;fi;'
        'if [ ! -e "$P" ]&&[ ! -L "$P" ];then '
        '[ "$WANT" != 1 ]||exit 71;printf "A90CACHE_TMP state=absent '
        'available_kib=%s inodes_available=%s enable=%s latch=%s\\n" "$A" "$I" "$e" "$l";exit 0;fi;'
        '[ "$WANT" != 0 ]||exit 72;[ ! -L "$P" ]&&[ -f "$P" ]||exit 73;'
        '[ "$(/bin/busybox readlink -f "$P")" = "$P" ]||exit 74;'
        'M=$(/bin/busybox stat -c "%F|%s|%a|%h|%u|%g|%d|%i|%b" "$P");'
        '[ "$M" = "$META" ]||exit 75;H=$(/bin/busybox sha256sum "$P");H=${H%% *};'
        '[ "$H" = "$S" ]||exit 76;m=0;for F in /proc/[0-9]*/mountinfo;do '
        '[ -r "$F" ]||continue;/bin/busybox grep -F "$P" "$F" >/dev/null 2>&1&&m=$((m+1));done;'
        'q=0;for F in /sys/block/loop*/loop/backing_file;do [ -r "$F" ]||continue;'
        'V=$(/bin/busybox cat "$F");[ "$V" = "$P" ]&&q=$((q+1));done;'
        'o=0;for F in /proc/[0-9]*/fd/*;do [ -e "$F" ]||continue;'
        'V=$(/bin/busybox readlink "$F")||continue;case "$V" in '
        '"$P"|"$P (deleted)")o=$((o+1));;esac;done;'
        'printf "A90CACHE_TMP state=present available_kib=%s inodes_available=%s '
        'enable=%s latch=%s meta=%s sha256=%s mount=%s loop=%s open=%s\\n" '
        '"$A" "$I" "$e" "$l" "$M" "$H" "$m" "$q" "$o"'
    ).replace('WANT="$4"', f'WANT={present}')


def _meta(cleanup: CleanupSpec) -> str:
    return (
        f"regular file|{cleanup.size}|{cleanup.mode:o}|{cleanup.nlink}|"
        f"{cleanup.uid}|{cleanup.gid}|{cleanup.device}|{cleanup.inode}|{cleanup.blocks}"
    )


def read_cleanup_state(
    args: argparse.Namespace,
    cleanup: CleanupSpec,
    *,
    require_present: bool | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    command = [
        "run", "/bin/busybox", "sh", "-c", _state_script(require_present),
        "a90-cache-tmp-state", cleanup.path, cleanup.sha256, _meta(cleanup),
    ]
    receipt = _command_receipt(args, command, "cache tmp state")
    return receipt, parse_cleanup_state_receipt(receipt, command, "cache tmp state")


def parse_cleanup_state_receipt(
    receipt: Any,
    command: list[str],
    label: str,
) -> dict[str, Any]:
    exact = base.require_exact_f1_command_receipt(receipt, command, label)
    matches = list(STATE_RE.finditer(str(exact.get("text") or "")))
    if len(matches) != 1:
        raise ContractError("cache tmp state marker is not unique")
    match = matches[0]
    result: dict[str, Any] = {
        "state": match.group("state"),
        "available_kib": int(match.group("available"), 10),
        "inodes_available": int(match.group("inodes"), 10),
        "enable": int(match.group("enable"), 10),
        "latch": int(match.group("latch"), 10),
    }
    if result["state"] == "present":
        result.update({
            "meta": match.group("meta"),
            "sha256": match.group("sha"),
            "mount": int(match.group("mount"), 10),
            "loop": int(match.group("loop"), 10),
            "open": int(match.group("open"), 10),
        })
    return result


def require_host_preserved(cleanup: CleanupSpec) -> dict[str, Any]:
    path = cleanup.host_preserved_path
    info = path.stat()
    if (
        path.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
        or info.st_size != cleanup.size
        or sha256_file(path) != cleanup.sha256
    ):
        raise ContractError("host-preserved cache bytes are not exact")
    return {"path": str(path), "size": info.st_size, "sha256": cleanup.sha256, "mode": 0o600}


def preserve_to_host(args: argparse.Namespace, cleanup: CleanupSpec) -> dict[str, Any]:
    destination = cleanup.host_preserved_path
    partial = destination.with_name(destination.name + ".partial")
    if destination.exists() or destination.is_symlink() or partial.exists() or partial.is_symlink():
        raise ContractError("host preservation destination is not fresh")
    destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    parent_info = destination.parent.lstat()
    if destination.parent.is_symlink() or not stat.S_ISDIR(parent_info.st_mode):
        raise ContractError("host preservation parent is not one private directory")
    os.chmod(destination.parent, 0o700)
    errors: list[BaseException] = []
    received = {"size": 0, "peer": None}
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((HOST_NCM_ADDRESS, 0))
    listener.listen(1)
    listener.settimeout(45.0)
    port = listener.getsockname()[1]

    def receive() -> None:
        try:
            connection, peer = listener.accept()
            with connection:
                connection.settimeout(45.0)
                received["peer"] = peer[0]
                if peer[0] != DEVICE_NCM_ADDRESS:
                    raise ContractError("preservation peer is not the exact A90 NCM address")
                descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "wb") as stream:
                    while True:
                        chunk = connection.recv(1024 * 1024)
                        if not chunk:
                            break
                        if received["size"] + len(chunk) > cleanup.size:
                            raise ContractError("host preservation exceeded bound size")
                        stream.write(chunk)
                        received["size"] += len(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
        except BaseException as exc:  # delivered to the caller after join
            errors.append(exc)
        finally:
            listener.close()

    thread = threading.Thread(target=receive, daemon=True)
    thread.start()
    command = [
        "run", "/bin/busybox", "sh", "-c",
        'exec /bin/busybox nc -n -w 30 "$1" "$2" < "$3"',
        "a90-cache-tmp-preserve", HOST_NCM_ADDRESS, str(port), cleanup.path,
    ]
    try:
        receipt = _command_receipt(args, command, "cache tmp host preservation")
    except Exception:
        listener.close()
        thread.join(timeout=2.0)
        raise
    thread.join(timeout=50.0)
    if thread.is_alive() or errors:
        raise ContractError(f"host preservation receiver failed: {errors!r}")
    if received["size"] != cleanup.size:
        raise ContractError("host preservation size changed")
    if sha256_file(partial) != cleanup.sha256:
        raise ContractError("host preservation sha256 changed")
    os.replace(partial, destination)
    os.chmod(destination, 0o600)
    return {"receipt": receipt, "host_preserved": require_host_preserved(cleanup)}


def _write_new(path: Path, action: str, payload: dict[str, Any]) -> None:
    if COMMON_RECORD_KEYS & set(payload):
        raise ContractError("journal payload may not replace schema or action")
    value = {"schema": JOURNAL_SCHEMA, "action": action, **payload}
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    parent_info = path.parent.lstat()
    if (
        path.parent.is_symlink()
        or not stat.S_ISDIR(parent_info.st_mode)
        or stat.S_IMODE(parent_info.st_mode) != 0o700
    ):
        raise ContractError("journal parent is not one exact private directory")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _read_journal_record(path: Path) -> dict[str, Any]:
    info = path.lstat()
    if (
        path.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise ContractError("cleanup journal member is not one private regular file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError("cleanup journal member is not an object")
    return value


def _validate_result_record(
    result: Any,
    cleanup: CleanupSpec,
    intent_sha256: str,
) -> dict[str, Any]:
    if (
        not isinstance(result, dict)
        or set(result) != RESULT_RECORD_KEYS
        or result.get("schema") != RESULT_SCHEMA
        or result.get("terminal") not in {
            "PASS_CACHE_TMP_RECLAIMED_RESIDENT_HEALTHY",
            "REFUTED_CACHE_TMP_UNLINK_EXACT_NO_EFFECT",
            "RECOVERY_PENDING_PARKED_NO_REPLAY",
        }
        or result.get("intent_sha256") != intent_sha256
        or result.get("unlink_dispatch_count") != 1
        or result.get("retransmit") is not False
        or result.get("host_preserved") != {
            "path": str(cleanup.host_preserved_path),
            "size": cleanup.size,
            "sha256": cleanup.sha256,
            "mode": 0o600,
        }
        or result.get("payload_transfer") is not False
        or result.get("partition_write") is not False
        or result.get("flash") is not False
        or result.get("s22plus_command_count") != 0
    ):
        raise ContractError("cleanup journal result binding changed")
    return result


def load_journal_prefix(
    cleanup: CleanupSpec,
    path: Path,
    expected_closure: str,
) -> list[dict[str, Any]]:
    closure = require_execution_closure(expected_closure)
    present = [name for name in JOURNAL_NAMES if (path / name).is_file()]
    if present != list(JOURNAL_NAMES[:len(present)]):
        raise ContractError("cleanup journal prefix is not contiguous")
    unexpected = sorted(
        item.name
        for item in path.glob("[0-9][0-9][0-9][0-9]-*.json")
        if item.name not in present
    )
    if unexpected:
        raise ContractError("cleanup journal has unexpected numbered members")
    payload_keys = (
        OPEN_RECORD_KEYS,
        INTENT_RECORD_KEYS,
        RESULT_JOURNAL_KEYS,
        CLOSED_RECORD_KEYS,
    )
    records: list[dict[str, Any]] = []
    for index, name in enumerate(present):
        record = _read_journal_record(path / name)
        if (
            set(record) != COMMON_RECORD_KEYS | payload_keys[index]
            or record.get("schema") != JOURNAL_SCHEMA
            or record.get("action") != JOURNAL_ACTIONS[index]
        ):
            raise ContractError("cleanup journal schema/action/key set changed")
        records.append(record)
    if not records:
        return records

    opened = records[0]
    expected_preserved = {
        "path": str(cleanup.host_preserved_path),
        "size": cleanup.size,
        "sha256": cleanup.sha256,
        "mode": 0o600,
    }
    status = parse_auto_status_receipt(
        opened.get("status_record"),
        "journal opening H2 status",
    )
    state_command = [
        "run", "/bin/busybox", "sh", "-c", _state_script(True),
        "a90-cache-tmp-state", cleanup.path, cleanup.sha256, _meta(cleanup),
    ]
    state = parse_cleanup_state_receipt(
        opened.get("state_record"),
        state_command,
        "journal opening cache state",
    )
    if (
        opened.get("manifest_sha256") != cleanup.manifest_sha256
        or opened.get("execution_closure") != closure
        or opened.get("host_preserved") != expected_preserved
        or not isinstance(opened.get("opening_health"), dict)
        or opened.get("status") != status
        or status != {"enable": 0, "latch": 0}
        or opened.get("state") != state
        or state.get("state") != "present"
        or state.get("available_kib") != 0
        or state.get("inodes_available", 0) <= 0
        or state.get("enable") != 0
        or state.get("latch") != 0
        or state.get("meta") != _meta(cleanup)
        or state.get("sha256") != cleanup.sha256
        or any(state.get(key) != 0 for key in ("mount", "loop", "open"))
    ):
        raise ContractError("cleanup journal opening binding changed")
    if len(records) == 1:
        return records

    intent = records[1]
    if (
        intent.get("manifest_sha256") != cleanup.manifest_sha256
        or intent.get("selected_path") != cleanup.path
        or intent.get("selected_sha256") != cleanup.sha256
        or intent.get("unlink_dispatch_count_max") != 1
        or intent.get("retransmit") is not False
        or intent.get("s22plus_command_count") != 0
    ):
        raise ContractError("cleanup journal intent binding changed")
    intent_sha256 = sha256_file(path / JOURNAL_NAMES[1])
    if len(records) >= 3:
        _validate_result_record(records[2]["result"], cleanup, intent_sha256)
    if len(records) >= 4:
        result = _validate_result_record(records[3]["result"], cleanup, intent_sha256)
        if (
            records[3].get("result_sha256") != _json_sha256(result)
            or records[2]["result"] != result
        ):
            raise ContractError("cleanup journal closure binding changed")
    return records


def _effect_script() -> str:
    return (
        'set -eu;P="$1";S="$2";META="$3";[ ! -L "$P" ]&&[ -f "$P" ]||exit 81;'
        'E=/cache/a90-auto-handoff-phase3-minimal-h2.enable;'
        'L=/cache/a90-auto-handoff-phase3-minimal-h2.done;'
        '[ ! -e "$E" ]&&[ ! -L "$E" ]&&[ ! -e "$L" ]&&[ ! -L "$L" ]||exit 80;'
        '[ "$(/bin/busybox readlink -f "$P")" = "$P" ]||exit 82;'
        '[ "$(/bin/busybox stat -c "%F|%s|%a|%h|%u|%g|%d|%i|%b" "$P")" = "$META" ]||exit 83;'
        'H=$(/bin/busybox sha256sum "$P");H=${H%% *};[ "$H" = "$S" ]||exit 84;'
        'for F in /proc/[0-9]*/mountinfo;do [ -r "$F" ]||continue;'
        '! /bin/busybox grep -F "$P" "$F" >/dev/null 2>&1||exit 85;done;'
        'for F in /sys/block/loop*/loop/backing_file;do [ -r "$F" ]||continue;'
        '[ "$(/bin/busybox cat "$F")" != "$P" ]||exit 86;done;'
        'for F in /proc/[0-9]*/fd/*;do [ -e "$F" ]||continue;'
        'V=$(/bin/busybox readlink "$F")||continue;case "$V" in '
        '"$P"|"$P (deleted)")exit 87;;esac;done;'
        '/bin/busybox rm -- "$P"||exit 88;/bin/busybox sync;'
        '[ ! -e "$P" ]&&[ ! -L "$P" ]||exit 89;echo A90CACHE_TMP_UNLINK removed=1'
    )


def execute_cleanup(
    resident_spec: resident.SessionSpec,
    cleanup: CleanupSpec,
    *,
    expected_closure: str,
    transaction_dir: Path,
    operator_attended: bool,
) -> dict[str, Any]:
    if operator_attended is not True:
        raise ContractError("operator attendance is required for cache cleanup")
    closure = require_execution_closure(expected_closure)
    if cleanup.execution_closure_sha256 != expected_closure:
        raise ContractError("cleanup manifest execution closure changed")
    path = transaction_dir.resolve()
    if PRIVATE_ROOT not in path.parents or path.exists() or path.is_symlink():
        raise ContractError("cleanup transaction directory is not one fresh private path")
    host_preserved = require_host_preserved(cleanup)
    opening_preflight, opening_health = resident.resident_d0_preflight(resident_spec)
    opening_preflight.validate()
    args = _effect_args()
    status_record, status = read_auto_status(args)
    state_record, state = read_cleanup_state(args, cleanup, require_present=True)
    if (
        status != {"enable": 0, "latch": 0}
        or state.get("available_kib") != 0
        or state.get("inodes_available", 0) <= 0
        or state.get("enable") != 0
        or state.get("latch") != 0
        or state.get("meta") != _meta(cleanup)
        or state.get("sha256") != cleanup.sha256
        or any(state.get(key) != 0 for key in ("mount", "loop", "open"))
    ):
        raise ContractError("fresh cache cleanup preflight is not exact")
    path.mkdir(parents=True, mode=0o700)
    os.chmod(path, 0o700)
    _write_new(path / "0000-open.json", "open-exact-present-unused", {
        "manifest_sha256": cleanup.manifest_sha256,
        "execution_closure": closure,
        "host_preserved": host_preserved,
        "opening_health": opening_health,
        "status_record": status_record,
        "status": status,
        "state_record": state_record,
        "state": state,
    })
    intent = {
        "manifest_sha256": cleanup.manifest_sha256,
        "selected_path": cleanup.path,
        "selected_sha256": cleanup.sha256,
        "unlink_dispatch_count_max": 1,
        "retransmit": False,
        "s22plus_command_count": 0,
    }
    _write_new(path / "0001-unlink-intent.json", "unlink-intent", intent)
    durable_prefix = load_journal_prefix(cleanup, path, expected_closure)
    if len(durable_prefix) != 2:
        raise ContractError("cleanup durable intent was not published exactly")
    intent_sha256 = sha256_file(path / "0001-unlink-intent.json")
    command = [
        "run", "/bin/busybox", "sh", "-c", _effect_script(),
        "a90-cache-tmp-unlink", cleanup.path, cleanup.sha256, _meta(cleanup),
    ]
    try:
        unlink_record: dict[str, Any] = base.run_f1_cmd(
            args,
            command,
            allow_error=True,
        )
    except Exception as exc:  # no retransmit; presence decides only classification
        unlink_record = {
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "response_proof": False,
        }
    try:
        post_state_record, post_state = read_cleanup_state(
            args,
            cleanup,
            require_present=None,
        )
        post_state_error = None
    except Exception as exc:
        post_state_record = None
        post_state = None
        post_state_error = {"type": type(exc).__name__, "message": str(exc)}
    try:
        final_preflight, final_health = resident.resident_d0_preflight(resident_spec)
        final_preflight.validate()
        final_health_error = None
    except Exception as exc:
        final_health = None
        final_health_error = {"type": type(exc).__name__, "message": str(exc)}
    try:
        final_status_record, final_status = read_auto_status(args)
        final_status_error = None
    except Exception as exc:
        final_status_record = None
        final_status = None
        final_status_error = {"type": type(exc).__name__, "message": str(exc)}
    exact_absent = (
        isinstance(post_state, dict)
        and post_state.get("state") == "absent"
        and post_state.get("available_kib", 0) > 0
        and post_state.get("enable") == 0
        and post_state.get("latch") == 0
    )
    exact_health = final_health is not None and final_status == {"enable": 0, "latch": 0}
    if exact_absent and exact_health:
        terminal = "PASS_CACHE_TMP_RECLAIMED_RESIDENT_HEALTHY"
    elif post_state is not None and post_state.get("state") == "present" and exact_health:
        terminal = "REFUTED_CACHE_TMP_UNLINK_EXACT_NO_EFFECT"
    else:
        terminal = "RECOVERY_PENDING_PARKED_NO_REPLAY"
    result = {
        "schema": RESULT_SCHEMA,
        "terminal": terminal,
        "intent_sha256": intent_sha256,
        "unlink_dispatch_count": 1,
        "retransmit": False,
        "unlink_record": unlink_record,
        "post_state_record": post_state_record,
        "post_state": post_state,
        "post_state_error": post_state_error,
        "final_health": final_health,
        "final_health_error": final_health_error,
        "final_status_record": final_status_record,
        "final_status": final_status,
        "final_status_error": final_status_error,
        "host_preserved": host_preserved,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
        "s22plus_command_count": 0,
    }
    _write_new(path / "0002-unlink-result.json", "unlink-result", {"result": result})
    result_prefix = load_journal_prefix(cleanup, path, expected_closure)
    if len(result_prefix) != 3:
        raise ContractError("cleanup result was not durably published exactly")
    if terminal == "PASS_CACHE_TMP_RECLAIMED_RESIDENT_HEALTHY":
        _write_new(path / "0003-closed.json", "closed", {
            "result_sha256": _json_sha256(result),
            "result": result,
        })
        closed_prefix = load_journal_prefix(cleanup, path, expected_closure)
        if len(closed_prefix) != 4:
            raise ContractError("cleanup closure was not durably published exactly")
    return result


def reconcile_cleanup(
    resident_spec: resident.SessionSpec,
    cleanup: CleanupSpec,
    *,
    expected_closure: str,
    transaction_dir: Path,
) -> dict[str, Any]:
    require_execution_closure(expected_closure)
    path = transaction_dir.resolve()
    if PRIVATE_ROOT not in path.parents or not path.is_dir() or path.is_symlink():
        raise ContractError("cleanup reconciliation path is not exact")
    records = load_journal_prefix(cleanup, path, expected_closure)
    present = list(JOURNAL_NAMES[:len(records)])
    if len(records) < 2:
        return {
            "schema": RESULT_SCHEMA,
            "terminal": "NO_DURABLE_UNLINK_INTENT",
            "unlink_dispatch_count": 0,
            "retransmit": False,
        }
    require_host_preserved(cleanup)
    args = _effect_args()
    try:
        state_record, state = read_cleanup_state(
            args,
            cleanup,
            require_present=None,
        )
        state_error = None
    except Exception as exc:
        state_record = None
        state = None
        state_error = {"type": type(exc).__name__, "message": str(exc)}
    try:
        _, health = resident.resident_d0_preflight(resident_spec)
        health_error = None
    except Exception as exc:
        health = None
        health_error = {"type": type(exc).__name__, "message": str(exc)}
    try:
        status_record, status = read_auto_status(args)
        status_error = None
    except Exception as exc:
        status_record = None
        status = None
        status_error = {"type": type(exc).__name__, "message": str(exc)}
    exact_unarmed_status = status == {"enable": 0, "latch": 0}
    if (
        isinstance(state, dict)
        and state.get("state") == "absent"
        and state.get("available_kib", 0) > 0
        and state.get("enable") == 0
        and state.get("latch") == 0
        and health is not None
        and exact_unarmed_status
    ):
        terminal = "PASS_CACHE_TMP_RECLAIMED_INFERRED_NO_REPLAY"
    elif (
        state is not None
        and state.get("state") == "present"
        and health is not None
        and exact_unarmed_status
    ):
        terminal = "REFUTED_CACHE_TMP_UNLINK_CURRENTLY_PRESENT_NO_REPLAY"
    else:
        terminal = "RECOVERY_PENDING_PARKED_NO_REPLAY"
    return {
        "schema": RESULT_SCHEMA,
        "terminal": terminal,
        "journal_records_present": present,
        "unlink_dispatch_count": None,
        "retransmit": False,
        "state_record": state_record,
        "state": state,
        "state_error": state_error,
        "resident_health": health,
        "resident_health_error": health_error,
        "auto_handoff_status_record": status_record,
        "auto_handoff_status": status,
        "auto_handoff_status_error": status_error,
        "s22plus_command_count": 0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-execution-closure", action="store_true")
    parser.add_argument("--cleanup-manifest", type=Path)
    parser.add_argument("--expect-cleanup-manifest-sha256")
    parser.add_argument("--resident-manifest", type=Path)
    parser.add_argument("--expect-resident-manifest-sha256")
    parser.add_argument("--expect-execution-closure-sha256")
    parser.add_argument("--transaction-dir", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--preserve", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--reconcile", action="store_true")
    parser.add_argument("--operator-attended", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.print_execution_closure:
        print(json.dumps(execution_closure(), indent=2, sort_keys=True))
        return 0
    required = (
        args.cleanup_manifest, args.expect_cleanup_manifest_sha256,
        args.resident_manifest, args.expect_resident_manifest_sha256,
        args.expect_execution_closure_sha256,
    )
    if any(value is None for value in required):
        raise ContractError("cleanup, resident, and execution bindings are required")
    cleanup = load_cleanup_spec(
        args.cleanup_manifest,
        args.expect_cleanup_manifest_sha256,
    )
    if cleanup.execution_closure_sha256 != args.expect_execution_closure_sha256:
        raise ContractError("manifest and CLI execution closures differ")
    require_execution_closure(args.expect_execution_closure_sha256)
    resident_spec = validate_resident_binding(
        cleanup,
        args.resident_manifest,
        args.expect_resident_manifest_sha256,
    )
    if args.preserve:
        opening_preflight, _ = resident.resident_d0_preflight(resident_spec)
        opening_preflight.validate()
        effect_args = _effect_args()
        _, status = read_auto_status(effect_args)
        _, state = read_cleanup_state(effect_args, cleanup, require_present=True)
        if (
            status != {"enable": 0, "latch": 0}
            or state.get("available_kib") != 0
            or any(state.get(key) != 0 for key in ("enable", "latch", "mount", "loop", "open"))
        ):
            raise ContractError("preservation D0 state is not exact")
        result = preserve_to_host(effect_args, cleanup)
    elif args.execute:
        if args.transaction_dir is None:
            raise ContractError("execute requires transaction directory")
        result = execute_cleanup(
            resident_spec,
            cleanup,
            expected_closure=args.expect_execution_closure_sha256,
            transaction_dir=args.transaction_dir,
            operator_attended=args.operator_attended,
        )
    elif args.reconcile:
        if args.transaction_dir is None:
            raise ContractError("reconcile requires transaction directory")
        result = reconcile_cleanup(
            resident_spec,
            cleanup,
            expected_closure=args.expect_execution_closure_sha256,
            transaction_dir=args.transaction_dir,
        )
    else:
        result = {
            "schema": SCHEMA,
            "host_only": True,
            "manifest_sha256": cleanup.manifest_sha256,
            "execution_closure": execution_closure(),
            "live_authority": False,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, resident.ContractError, base.ContractError) as exc:
        print(f"a90-cache-tmp-cleanup-v1: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
