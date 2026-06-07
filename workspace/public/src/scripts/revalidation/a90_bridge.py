#!/usr/bin/env python3
"""Manage the A90 native-init serial bridge from a stable repo entrypoint."""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import grp
import json
import os
import pwd
import signal
import socket
import stat
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from _workspace_bootstrap import repo_root
from a90_serial_lock import SerialBridgeLock, SerialBridgeLockBusy


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_DEVICE = "auto"
DEFAULT_DEVICE_GLOB = "/dev/serial/by-id/usb-SAMSUNG_SAMSUNG_Android_*"
BRIDGE_WRAPPER_CONTRACT = 1
TCP_LISTEN_STATE = "0A"
BRIDGE_SCRIPT_REL = "workspace/public/src/scripts/revalidation/serial_tcp_bridge.py"
PRIVATE_RUN_REL = "workspace/private/run"
PRIVATE_LOG_REL = "workspace/private/logs/bridge"
PRIVATE_REPAIR_RELS = (PRIVATE_LOG_REL, PRIVATE_RUN_REL)
MANAGED_NAME = "a90_bridge"


@dataclass
class SerialCandidate:
    path: str
    realpath: str
    exists: bool


@dataclass
class BridgeProcess:
    pid: int
    cmdline: str
    managed: bool
    port_match: bool


def log(message: str) -> None:
    print(f"[a90-bridge] {message}", file=sys.stderr, flush=True)


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path)


def now_label() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def default_metadata_path(root: Path) -> Path:
    return root / PRIVATE_RUN_REL / f"{MANAGED_NAME}.json"


def default_capture_path(root: Path) -> Path:
    return root / PRIVATE_LOG_REL / f"bridge-{now_label()}.raw.log"


def default_stderr_path(root: Path) -> Path:
    return root / PRIVATE_LOG_REL / f"bridge-{now_label()}.stderr.log"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def process_cmdline(pid: int) -> str:
    return " ".join(process_cmdline_parts(pid))


def process_cmdline_parts(pid: int) -> list[str]:
    raw = Path("/proc") / str(pid) / "cmdline"
    try:
        data = raw.read_bytes()
    except OSError:
        return []
    return [part.decode("utf-8", errors="replace") for part in data.split(b"\0") if part]


def managed_pid(metadata_path: Path) -> int | None:
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    pid = payload.get("pid")
    return pid if isinstance(pid, int) else None


def is_bridge_cmdline(cmdline: str) -> bool:
    return any(Path(part).name == "serial_tcp_bridge.py" for part in cmdline.split())


def is_bridge_process(pid: int) -> bool:
    return any(Path(part).name == "serial_tcp_bridge.py" for part in process_cmdline_parts(pid))


def cmdline_port_match(cmdline: str, port: int) -> bool:
    parts = cmdline.split()
    text_port = str(port)
    for index, part in enumerate(parts):
        if part == "--port" and index + 1 < len(parts) and parts[index + 1] == text_port:
            return True
        if part.startswith("--port=") and part.split("=", 1)[1] == text_port:
            return True
    return "--port" not in parts and port == DEFAULT_PORT


def discover_bridge_processes(port: int, metadata_path: Path) -> list[BridgeProcess]:
    pid_from_metadata = managed_pid(metadata_path)
    processes: list[BridgeProcess] = []
    proc_root = Path("/proc")
    for item in proc_root.iterdir():
        if not item.name.isdigit():
            continue
        pid = int(item.name)
        cmdline = process_cmdline(pid)
        if not is_bridge_process(pid):
            continue
        processes.append(
            BridgeProcess(
                pid=pid,
                cmdline=cmdline,
                managed=pid_from_metadata == pid,
                port_match=cmdline_port_match(cmdline, port),
            )
        )
    return sorted(processes, key=lambda process: (not process.managed, process.pid))


def parse_proc_tcp_line(line: str) -> tuple[str, int, str, str, int] | None:
    parts = line.split()
    if len(parts) < 10:
        return None
    local = parts[1]
    state = parts[3]
    uid = int(parts[7], 10)
    inode = parts[9]
    if ":" not in local:
        return None
    address_hex, port_hex = local.split(":", 1)
    if len(address_hex) != 8:
        return None
    octets = [str(int(address_hex[index:index + 2], 16)) for index in range(6, -1, -2)]
    return ".".join(octets), int(port_hex, 16), state, inode, uid


def listen_sockets(host: str, port: int) -> list[dict[str, Any]]:
    path = Path("/proc/net/tcp")
    sockets: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[1:]
    except OSError:
        return sockets
    for line in lines:
        parsed = parse_proc_tcp_line(line)
        if parsed is None:
            continue
        address, local_port, state, inode, uid = parsed
        if local_port != port or state != TCP_LISTEN_STATE:
            continue
        if address not in {host, "0.0.0.0"}:
            continue
        sockets.append({
            "address": address,
            "port": local_port,
            "inode": inode,
            "uid": uid,
        })
    return sockets


def listen_inodes(host: str, port: int) -> list[str]:
    return [item["inode"] for item in listen_sockets(host, port)]


def pid_lookup_for_socket_inodes(inodes: list[str]) -> dict[str, Any]:
    wanted = {f"socket:[{inode}]" for inode in inodes}
    pids: set[int] = set()
    inaccessible_fd_dirs = 0
    scanned_fd_dirs = 0
    if not wanted:
        return {
            "pids": [],
            "source": "none",
            "scanned_fd_dirs": 0,
            "inaccessible_fd_dirs": 0,
        }
    for item in Path("/proc").iterdir():
        if not item.name.isdigit():
            continue
        fd_dir = item / "fd"
        try:
            fds = list(fd_dir.iterdir())
        except OSError:
            inaccessible_fd_dirs += 1
            continue
        scanned_fd_dirs += 1
        for fd in fds:
            try:
                target = os.readlink(fd)
            except OSError:
                continue
            if target in wanted:
                pids.add(int(item.name))
                break
    return {
        "pids": sorted(pids),
        "source": "fd" if pids else "unresolved",
        "scanned_fd_dirs": scanned_fd_dirs,
        "inaccessible_fd_dirs": inaccessible_fd_dirs,
    }


def pids_for_socket_inodes(inodes: list[str]) -> list[int]:
    return pid_lookup_for_socket_inodes(inodes)["pids"]


def probe_bridge_client(host: str, port: int) -> str:
    try:
        with SerialBridgeLock(timeout_sec=0.0, purpose="a90_bridge:probe"):
            try:
                with socket.create_connection((host, port), timeout=0.25) as sock:
                    sock.settimeout(0.25)
                    try:
                        data = sock.recv(256)
                    except socket.timeout:
                        return "connected-no-immediate-error"
                    if b"serial device is not connected" in data:
                        return "serial-missing"
                    if b"busy: another client is active" in data:
                        return "busy-bridge-client"
                    if data == b"":
                        return "closed"
                    return "data"
            except ConnectionRefusedError:
                return "not-listening"
            except OSError as exc:
                return f"error:{exc.__class__.__name__}"
    except SerialBridgeLockBusy:
        return "busy-serial-lock"


def serial_candidates(device_glob: str) -> list[SerialCandidate]:
    candidates: list[SerialCandidate] = []
    for path_text in sorted(glob.glob(device_glob)):
        path = Path(path_text)
        candidates.append(
            SerialCandidate(
                path=path_text,
                realpath=os.path.realpath(path_text),
                exists=path.exists(),
            )
        )
    return candidates


def selected_device_info(device: str, device_glob: str) -> dict[str, Any]:
    candidates = serial_candidates(device_glob)
    ambiguous = device == "auto" and len(candidates) > 1
    selected = ""
    selected_realpath = ""
    if device != "auto":
        selected = device
        selected_realpath = os.path.realpath(device)
    elif len(candidates) == 1:
        selected = candidates[0].path
        selected_realpath = candidates[0].realpath
    elif candidates:
        selected = candidates[0].path
        selected_realpath = candidates[0].realpath
    return {
        "serial_candidates": [asdict(candidate) for candidate in candidates],
        "selected_device": selected,
        "selected_realpath": selected_realpath,
        "ambiguous": ambiguous,
    }


def collect_status(args: argparse.Namespace, root: Path) -> dict[str, Any]:
    metadata_path = Path(args.metadata).resolve() if args.metadata else default_metadata_path(root)
    port_sockets = listen_sockets(args.host, args.port)
    inodes = [item["inode"] for item in port_sockets]
    pid_lookup = pid_lookup_for_socket_inodes(inodes)
    processes = discover_bridge_processes(args.port, metadata_path)
    managed = next((process for process in processes if process.managed), None)
    port_bridge_processes = [process for process in processes if process.port_match]
    if not pid_lookup["pids"] and port_bridge_processes:
        pid_lookup["pids"] = [process.pid for process in port_bridge_processes]
        pid_lookup["source"] = "cmdline-fallback"
    if managed is not None and process_exists(managed.pid):
        bridge_state = "running"
    elif port_bridge_processes:
        bridge_state = "running"
    elif inodes:
        bridge_state = "unknown"
    else:
        bridge_state = "stopped"

    metadata: dict[str, Any] = {}
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        metadata = {}

    return {
        "wrapper_contract": BRIDGE_WRAPPER_CONTRACT,
        "wrapper_name": MANAGED_NAME,
        "bridge_process": bridge_state,
        "listen_host": args.host,
        "listen_port": args.port,
        "port_listening": bool(inodes),
        "bridge_probe": "skipped" if args.no_client_probe else probe_bridge_client(args.host, args.port),
        "port_sockets": port_sockets,
        "port_socket_inodes": inodes,
        "port_pids": pid_lookup["pids"],
        "port_pid_source": pid_lookup["source"],
        "port_pid_scanned_fd_dirs": pid_lookup["scanned_fd_dirs"],
        "port_pid_inaccessible_fd_dirs": pid_lookup["inaccessible_fd_dirs"],
        "metadata_path": rel(metadata_path, root),
        "metadata_present": metadata_path.exists(),
        "metadata": metadata,
        "capture_path": metadata.get("capture_path", ""),
        "processes": [asdict(process) for process in processes],
        **selected_device_info(args.device, args.device_glob),
    }


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def print_status_text(status: dict[str, Any]) -> None:
    print(f"wrapper_contract={status['wrapper_contract']}")
    print(f"bridge_process={status['bridge_process']}")
    print(f"listen={status['listen_host']}:{status['listen_port']}")
    print(f"port_listening={int(bool(status['port_listening']))}")
    print(f"bridge_probe={status['bridge_probe']}")
    print(f"port_pids={','.join(str(pid) for pid in status['port_pids']) or '-'}")
    print(f"port_pid_source={status['port_pid_source']}")
    print(f"port_pid_inaccessible_fd_dirs={status['port_pid_inaccessible_fd_dirs']}")
    print(f"metadata_path={status['metadata_path']}")
    print(f"metadata_present={int(bool(status['metadata_present']))}")
    print(f"capture_path={status['capture_path'] or '-'}")
    print(f"selected_device={status['selected_device'] or '-'}")
    print(f"selected_realpath={status['selected_realpath'] or '-'}")
    print(f"ambiguous={int(bool(status['ambiguous']))}")
    print(f"serial_candidates={len(status['serial_candidates'])}")
    for process in status["processes"]:
        marker = "managed" if process["managed"] else "discovered"
        print(f"process={process['pid']} {marker} port_match={int(process['port_match'])}")


def add_check(checks: list[dict[str, str]], name: str, status: str, detail: str) -> None:
    checks.append({"name": name, "status": status, "detail": detail})


def group_names() -> list[str]:
    names: list[str] = []
    for gid in os.getgroups():
        try:
            names.append(grp.getgrgid(gid).gr_name)
        except KeyError:
            names.append(str(gid))
    return sorted(set(names))


def stat_info(path: Path) -> dict[str, Any]:
    try:
        item = path.stat()
    except OSError as exc:
        return {"exists": False, "error": str(exc)}
    try:
        user = pwd.getpwuid(item.st_uid).pw_name
    except KeyError:
        user = str(item.st_uid)
    try:
        group = grp.getgrgid(item.st_gid).gr_name
    except KeyError:
        group = str(item.st_gid)
    return {
        "exists": True,
        "mode": stat.filemode(item.st_mode),
        "uid": item.st_uid,
        "gid": item.st_gid,
        "user": user,
        "group": group,
        "size": item.st_size,
    }


def path_writable(path: Path) -> bool:
    target = path if path.exists() else path.parent
    return os.access(target, os.W_OK)


def path_detail(path: Path, root: Path) -> str:
    info = stat_info(path)
    if not info.get("exists"):
        return f"path={rel(path, root)} exists=0 writable={int(path_writable(path))}"
    return (
        f"path={rel(path, root)} exists=1 writable={int(path_writable(path))} "
        f"owner={info.get('user')}:{info.get('group')} mode={info.get('mode')}"
    )


def private_dir_repair_hint(root: Path) -> str:
    script = root / "workspace/public/src/scripts/revalidation/a90_bridge.py"
    try:
        user = pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        user = str(os.getuid())
    return f"sudo python3 {rel(script, root)} repair-dirs --user {user}"


def private_dir_needs_repair(root: Path) -> bool:
    return any(not path_writable(root / item) for item in PRIVATE_REPAIR_RELS)


def target_identity(user: str | None) -> tuple[int, int, str, str]:
    if user:
        entry = pwd.getpwnam(user)
        group = grp.getgrgid(entry.pw_gid).gr_name
        return entry.pw_uid, entry.pw_gid, entry.pw_name, group
    if os.geteuid() == 0 and os.environ.get("SUDO_UID"):
        uid = int(os.environ["SUDO_UID"], 10)
        gid = int(os.environ.get("SUDO_GID", uid), 10)
        try:
            username = pwd.getpwuid(uid).pw_name
        except KeyError:
            username = os.environ.get("SUDO_USER", str(uid))
        try:
            group_name = grp.getgrgid(gid).gr_name
        except KeyError:
            group_name = str(gid)
        return uid, gid, username, group_name
    uid = os.getuid()
    gid = os.getgid()
    try:
        username = pwd.getpwuid(uid).pw_name
    except KeyError:
        username = str(uid)
    try:
        group_name = grp.getgrgid(gid).gr_name
    except KeyError:
        group_name = str(gid)
    return uid, gid, username, group_name


def ensure_user_write_bits(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return
    if stat.S_ISLNK(mode):
        return
    if path.is_dir():
        desired = mode | stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
    else:
        desired = mode | stat.S_IRUSR | stat.S_IWUSR
    if desired != mode:
        os.chmod(path, stat.S_IMODE(desired))


def chown_tree(path: Path, uid: int, gid: int) -> int:
    changed = 0
    targets = [path]
    if path.is_dir():
        for dirpath, dirnames, filenames in os.walk(path):
            current = Path(dirpath)
            targets.extend(current / item for item in dirnames)
            targets.extend(current / item for item in filenames)
    for target in targets:
        try:
            item = target.lstat()
            if item.st_uid != uid or item.st_gid != gid:
                os.chown(target, uid, gid, follow_symlinks=False)
                changed += 1
            ensure_user_write_bits(target)
        except OSError:
            continue
    return changed


def command_repair_dirs(args: argparse.Namespace, root: Path) -> int:
    try:
        uid, gid, username, group_name = target_identity(args.user)
    except (KeyError, ValueError) as exc:
        payload = {"ok": False, "error": f"target-user: {exc}"}
        if args.json:
            print_json(payload)
        else:
            print(f"repair_dirs_ok=0 error={payload['error']}")
        return 1

    results: list[dict[str, Any]] = []
    needs_sudo = False
    changed = 0
    for item in PRIVATE_REPAIR_RELS:
        path = root / item
        before = stat_info(path)
        created = False
        repaired = False
        error = ""
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                created = True
            except OSError as exc:
                error = str(exc)
                needs_sudo = True
        if not error and not path_writable(path):
            if os.geteuid() != 0:
                needs_sudo = True
            else:
                changed += chown_tree(path, uid, gid)
                repaired = True
        elif not error and os.geteuid() == 0:
            changed += chown_tree(path, uid, gid)
            repaired = True
        if not error and path.exists():
            try:
                ensure_user_write_bits(path)
            except OSError as exc:
                error = str(exc)
        after = stat_info(path)
        results.append({
            "path": rel(path, root),
            "created": created,
            "repaired": repaired,
            "before": before,
            "after": after,
            "writable": path_writable(path),
            "error": error,
        })

    ok = all(item["writable"] and not item["error"] for item in results)
    payload = {
        "ok": ok,
        "needs_sudo": needs_sudo and not ok,
        "target": {
            "uid": uid,
            "gid": gid,
            "user": username,
            "group": group_name,
        },
        "changed": changed,
        "sudo_command": private_dir_repair_hint(root),
        "dirs": results,
    }
    if args.json:
        print_json(payload)
    else:
        print(f"repair_dirs_ok={int(ok)} needs_sudo={int(payload['needs_sudo'])} target={username}:{group_name}")
        for item in results:
            print(
                f"dir={item['path']} writable={int(item['writable'])} "
                f"created={int(item['created'])} repaired={int(item['repaired'])} "
                f"owner={item['after'].get('user')}:{item['after'].get('group')} "
                f"mode={item['after'].get('mode')} error={item['error'] or '-'}"
            )
        if payload["needs_sudo"]:
            print(f"sudo_command={payload['sudo_command']}")
    if ok:
        return 0
    return 2 if payload["needs_sudo"] else 1


def inspect_pycache(script_dir: Path) -> dict[str, Any]:
    path = script_dir / "__pycache__"
    info = stat_info(path)
    entries: list[dict[str, Any]] = []
    if path.is_dir():
        for child in sorted(path.iterdir()):
            item = stat_info(child)
            item["path"] = str(child)
            entries.append(item)
    return {"path": str(path), "info": info, "entries": entries}


def command_doctor(args: argparse.Namespace, root: Path) -> int:
    status = collect_status(args, root)
    script_path = root / BRIDGE_SCRIPT_REL
    script_dir = script_path.parent
    selected_realpath = status.get("selected_realpath") or ""
    selected_path = Path(selected_realpath) if selected_realpath else None
    pycache = inspect_pycache(script_dir)
    groups = group_names()
    metadata = status.get("metadata", {})
    capture_path = root / metadata["capture_path"] if metadata.get("capture_path") else None
    stderr_path = root / metadata["stderr_log"] if metadata.get("stderr_log") else None
    checks: list[dict[str, str]] = []

    add_check(
        checks,
        "bridge_script_exists",
        "pass" if script_path.is_file() else "fail",
        rel(script_path, root),
    )
    add_check(
        checks,
        "serial_candidate",
        "pass" if status["serial_candidates"] else "fail",
        f"candidates={len(status['serial_candidates'])}",
    )
    add_check(
        checks,
        "serial_ambiguous",
        "fail" if status["ambiguous"] else "pass",
        f"ambiguous={int(bool(status['ambiguous']))}",
    )
    if selected_path is None:
        add_check(checks, "selected_serial_access", "fail", "selected_realpath=-")
    else:
        readable = os.access(selected_path, os.R_OK)
        writable = os.access(selected_path, os.W_OK)
        serial_status = "pass" if readable and writable else "warn"
        add_check(
            checks,
            "selected_serial_access",
            serial_status,
            f"path={selected_realpath} read={int(readable)} write={int(writable)}",
        )
    if os.geteuid() == 0 or "dialout" in groups:
        add_check(checks, "host_dialout_group", "pass", f"euid={os.geteuid()} groups={','.join(groups)}")
    else:
        add_check(checks, "host_dialout_group", "warn", f"euid={os.geteuid()} groups={','.join(groups)}")
    add_check(
        checks,
        "bridge_process",
        "pass" if status["bridge_process"] == "running" else "warn",
        f"state={status['bridge_process']}",
    )
    add_check(
        checks,
        "bridge_probe",
        "pass" if status["bridge_probe"] in {
            "connected-no-immediate-error",
            "data",
            "skipped",
            "busy-serial-lock",
            "busy-bridge-client",
        } else "warn",
        f"probe={status['bridge_probe']}",
    )
    pid_source = status["port_pid_source"]
    add_check(
        checks,
        "port_pid_resolution",
        "pass" if pid_source == "fd" else ("warn" if pid_source == "cmdline-fallback" else "fail"),
        f"source={pid_source} pids={status['port_pids']} inaccessible_fd_dirs={status['port_pid_inaccessible_fd_dirs']}",
    )
    metadata_pid = metadata.get("pid")
    metadata_ok = isinstance(metadata_pid, int) and process_exists(metadata_pid)
    add_check(
        checks,
        "metadata_pid",
        "pass" if metadata_ok else "warn",
        f"metadata_present={int(bool(status['metadata_present']))} pid={metadata_pid}",
    )
    private_log = root / PRIVATE_LOG_REL
    private_run = root / PRIVATE_RUN_REL
    add_check(
        checks,
        "private_log_dir",
        "pass" if path_writable(private_log) else "warn",
        path_detail(private_log, root),
    )
    add_check(
        checks,
        "private_run_dir",
        "pass" if path_writable(private_run) else "warn",
        path_detail(private_run, root),
    )
    if capture_path is not None:
        add_check(
            checks,
            "capture_path_private",
            "pass" if str(capture_path.resolve()).startswith(str((root / "workspace/private").resolve())) else "warn",
            rel(capture_path, root),
        )
    if stderr_path is not None:
        add_check(
            checks,
            "stderr_log_private",
            "pass" if str(stderr_path.resolve()).startswith(str((root / "workspace/private").resolve())) else "warn",
            rel(stderr_path, root),
        )

    pycache_entries = pycache["entries"]
    foreign_pycache = [
        item for item in pycache_entries
        if item.get("exists") and item.get("uid") not in {os.getuid(), os.geteuid()}
    ]
    add_check(
        checks,
        "pycache_hygiene",
        "warn" if foreign_pycache else "pass",
        f"entries={len(pycache_entries)} foreign_uid_entries={len(foreign_pycache)}",
    )

    fail_count = sum(1 for item in checks if item["status"] == "fail")
    warn_count = sum(1 for item in checks if item["status"] == "warn")
    payload = {
        "summary": {
            "ok": fail_count == 0,
            "fail": fail_count,
            "warn": warn_count,
        },
        "host": {
            "uid": os.getuid(),
            "euid": os.geteuid(),
            "user": pwd.getpwuid(os.getuid()).pw_name,
            "groups": groups,
            "cwd": os.getcwd(),
            "repo_root": str(root),
            "python": sys.executable,
        },
        "status": status,
        "selected_serial_stat": stat_info(selected_path) if selected_path is not None else {"exists": False},
        "bridge_script_stat": stat_info(script_path),
        "pycache": pycache,
        "checks": checks,
    }
    if args.json:
        print_json(payload)
    else:
        print(f"doctor_ok={int(payload['summary']['ok'])} fail={fail_count} warn={warn_count}")
        for item in checks:
            print(f"{item['status']} {item['name']}: {item['detail']}")
        if foreign_pycache:
            print(f"cleanup_hint=sudo rm -rf {rel(script_dir / '__pycache__', root)}")
        if private_dir_needs_repair(root):
            print(f"dir_repair_hint={private_dir_repair_hint(root)}")
    return 0 if fail_count == 0 else 1


def build_bridge_command(args: argparse.Namespace,
                         root: Path,
                         capture_path: Path) -> list[str]:
    bridge_script = root / BRIDGE_SCRIPT_REL
    expect_realpath = effective_expect_realpath(args)
    command = [
        args.python,
        str(bridge_script),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--device",
        args.device,
        "--device-glob",
        args.device_glob,
        "--capture",
        str(capture_path),
    ]
    if expect_realpath:
        command.extend(["--expect-realpath", expect_realpath])
    if args.allow_device_change:
        command.append("--allow-device-change")
    if args.no_pin_device:
        command.append("--no-pin-device")
    if args.allow_multiple_auto_matches:
        command.append("--allow-multiple-auto-matches")
    if args.assert_dtr_rts:
        command.append("--assert-dtr-rts")
    if args.no_exclusive_tty:
        command.append("--no-exclusive-tty")
    return command


def effective_expect_realpath(args: argparse.Namespace) -> str:
    if args.expect_realpath:
        return os.path.realpath(args.expect_realpath)
    if not args.pin_selected_realpath:
        return ""
    info = selected_device_info(args.device, args.device_glob)
    return str(info.get("selected_realpath") or "")


def write_metadata(metadata_path: Path, payload: dict[str, Any]) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def command_preflight(args: argparse.Namespace, root: Path) -> int:
    status = collect_status(args, root)
    status["ok"] = not status["ambiguous"]
    if args.json:
        print_json(status)
    else:
        print_status_text(status)
        print(f"ok={int(status['ok'])}")
    return 0 if status["ok"] else 2


def command_status(args: argparse.Namespace, root: Path) -> int:
    status = collect_status(args, root)
    if args.json:
        print_json(status)
    else:
        print_status_text(status)
    return 0


def command_start(args: argparse.Namespace, root: Path) -> int:
    metadata_path = Path(args.metadata).resolve() if args.metadata else default_metadata_path(root)
    capture_path = Path(args.capture).resolve() if args.capture else default_capture_path(root)
    stderr_path = Path(args.stderr_log).resolve() if args.stderr_log else default_stderr_path(root)
    status = collect_status(args, root)
    if status["ambiguous"] and not args.allow_multiple_auto_matches:
        log("refusing start: ambiguous Samsung ACM candidates")
        print_status_text(status)
        return 2
    if status["port_listening"]:
        log("refusing start: listener port is already busy")
        print_status_text(status)
        return 2

    capture_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_bridge_command(args, root, capture_path)
    stderr_fp = stderr_path.open("ab", buffering=0)
    try:
        process = subprocess.Popen(
            command,
            cwd=str(root),
            stdin=subprocess.DEVNULL,
            stdout=stderr_fp,
            stderr=stderr_fp,
            start_new_session=True,
        )
    finally:
        stderr_fp.close()

    metadata = {
        "wrapper_contract": BRIDGE_WRAPPER_CONTRACT,
        "pid": process.pid,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "command": command,
        "capture_path": rel(capture_path, root),
        "stderr_log": rel(stderr_path, root),
        "host": args.host,
        "port": args.port,
        "device": args.device,
        "device_glob": args.device_glob,
        "pin_selected_realpath": args.pin_selected_realpath,
        "effective_expect_realpath": effective_expect_realpath(args),
    }
    write_metadata(metadata_path, metadata)
    log(f"started bridge pid={process.pid}")
    log(f"capture={rel(capture_path, root)}")
    log(f"stderr_log={rel(stderr_path, root)}")

    if args.wait:
        deadline = time.monotonic() + args.wait_timeout
        while time.monotonic() < deadline:
            current = collect_status(args, root)
            if current["port_listening"]:
                break
            if not process_exists(process.pid):
                log("bridge process exited before listener became ready")
                return 1
            time.sleep(0.1)
    return 0


def command_ensure(args: argparse.Namespace, root: Path) -> int:
    status = collect_status(args, root)
    if status["bridge_process"] == "running":
        if args.json:
            print_json(status)
        else:
            print_status_text(status)
        return 0

    if status["port_listening"]:
        log("refusing ensure: listener port is busy but no bridge process was identified")
        if args.json:
            print_json(status)
        else:
            print_status_text(status)
        return 2

    start_rc = command_start(args, root)
    if start_rc != 0:
        return start_rc

    refreshed = collect_status(args, root)
    if args.json:
        print_json(refreshed)
    else:
        print_status_text(refreshed)
    return 0


def stop_pid(pid: int, timeout_sec: float) -> bool:
    if not process_exists(pid):
        return True
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if not process_exists(pid):
            return True
        time.sleep(0.1)
    return not process_exists(pid)


def command_stop(args: argparse.Namespace, root: Path) -> int:
    metadata_path = Path(args.metadata).resolve() if args.metadata else default_metadata_path(root)
    status = collect_status(args, root)
    targets: list[int] = []
    metadata_pid = managed_pid(metadata_path)
    if metadata_pid is not None:
        targets.append(metadata_pid)
    elif args.discovered:
        targets.extend(process["pid"] for process in status["processes"] if process["port_match"])
    else:
        if status["processes"]:
            log("no managed pidfile; refusing to stop discovered bridge without --discovered")
            print_status_text(status)
            return 2
        log("bridge is not running")
        return 0

    failed: list[int] = []
    for pid in sorted(set(targets)):
        cmdline = process_cmdline(pid)
        if not is_bridge_process(pid):
            log(f"refusing to stop pid={pid}: not a serial_tcp_bridge.py process")
            failed.append(pid)
            continue
        log(f"stopping bridge pid={pid}")
        if not stop_pid(pid, args.stop_timeout):
            failed.append(pid)

    if not failed and metadata_path.exists():
        try:
            metadata_path.unlink()
        except OSError as exc:
            log(f"warning: failed to remove metadata: {exc}")
    if failed:
        log("failed to stop pid(s): " + ",".join(str(pid) for pid in failed))
        return 1
    return 0


def command_restart(args: argparse.Namespace, root: Path) -> int:
    stop_rc = command_stop(args, root)
    if stop_rc not in {0}:
        return stop_rc
    time.sleep(0.3)
    return command_start(args, root)


def add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default=DEFAULT_HOST, help="bridge listen host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="bridge listen port")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="serial device path or auto")
    parser.add_argument("--device-glob", default=DEFAULT_DEVICE_GLOB, help="auto serial glob")
    parser.add_argument("--metadata", help="managed bridge metadata path")
    parser.add_argument("--expect-realpath", help="require resolved serial realpath")
    parser.add_argument("--pin-selected-realpath", action="store_true", help="pass selected serial realpath as --expect-realpath")
    parser.add_argument("--allow-device-change", action="store_true")
    parser.add_argument("--no-pin-device", action="store_true")
    parser.add_argument("--allow-multiple-auto-matches", action="store_true")
    parser.add_argument("--assert-dtr-rts", action="store_true")
    parser.add_argument("--no-exclusive-tty", action="store_true")
    parser.add_argument("--no-client-probe", action="store_true", help="skip localhost bridge probe")
    parser.add_argument("--json", action="store_true", help="emit JSON")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="Python executable for bridge start")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("preflight", "status", "doctor"):
        subparser = subparsers.add_parser(name)
        add_common_options(subparser)

    repair_dirs = subparsers.add_parser("repair-dirs")
    repair_dirs.add_argument("--user", help="target owner; default is SUDO_USER or current user")
    repair_dirs.add_argument("--json", action="store_true", help="emit JSON")

    start = subparsers.add_parser("start")
    add_common_options(start)
    start.add_argument("--capture", help="raw bridge capture path")
    start.add_argument("--stderr-log", help="bridge stdout/stderr log path")
    start.add_argument("--no-wait", dest="wait", action="store_false", help="do not wait for listener")
    start.add_argument("--wait-timeout", type=float, default=5.0)
    start.set_defaults(wait=True)

    ensure = subparsers.add_parser("ensure")
    add_common_options(ensure)
    ensure.add_argument("--capture", help="raw bridge capture path when starting")
    ensure.add_argument("--stderr-log", help="bridge stdout/stderr log path when starting")
    ensure.add_argument("--no-wait", dest="wait", action="store_false", help="do not wait for listener")
    ensure.add_argument("--wait-timeout", type=float, default=5.0)
    ensure.set_defaults(wait=True)

    stop = subparsers.add_parser("stop")
    add_common_options(stop)
    stop.add_argument("--discovered", action="store_true", help="stop discovered non-managed bridge")
    stop.add_argument("--stop-timeout", type=float, default=5.0)

    restart = subparsers.add_parser("restart")
    add_common_options(restart)
    restart.add_argument("--capture", help="raw bridge capture path")
    restart.add_argument("--stderr-log", help="bridge stdout/stderr log path")
    restart.add_argument("--discovered", action="store_true", help="stop discovered non-managed bridge")
    restart.add_argument("--stop-timeout", type=float, default=5.0)
    restart.add_argument("--no-wait", dest="wait", action="store_false", help="do not wait for listener")
    restart.add_argument("--wait-timeout", type=float, default=5.0)
    restart.set_defaults(wait=True)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    if args.command == "preflight":
        return command_preflight(args, root)
    if args.command == "status":
        return command_status(args, root)
    if args.command == "doctor":
        return command_doctor(args, root)
    if args.command == "repair-dirs":
        return command_repair_dirs(args, root)
    if args.command == "start":
        return command_start(args, root)
    if args.command == "ensure":
        return command_ensure(args, root)
    if args.command == "stop":
        return command_stop(args, root)
    if args.command == "restart":
        return command_restart(args, root)
    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
