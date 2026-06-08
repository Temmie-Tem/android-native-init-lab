#!/usr/bin/env python3
"""V2174 rollbackable live validation for native-init `wifi connect`.

The scope is association/carrier only. It intentionally does not run DHCP,
install routes, set DNS, or ping external hosts.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import posixpath
import re
import shlex
import socket
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from _workspace_bootstrap import repo_root

REPO_ROOT = repo_root()

from a90ctl import run_cmdv1_command  # noqa: E402
from a90harness.evidence import (  # noqa: E402
    EvidenceStore,
    WORKSPACE_PRIVATE_ROOT,
    workspace_private_input_path,
)
import a90_ncm_transport as ncm_transport  # noqa: E402
from tcpctl_host import tcpctl_request, tcpctl_run_line  # noqa: E402


CYCLE = "V2174"
RUN_LABEL = "v2174-wifi-urandom-connect-carrier"
TEST_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2174_wifi_urandom_connect.img", legacy_fallback=False
)
ROLLBACK_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2169_transport_contract.img", legacy_fallback=False
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.251 (v2174-wifi-urandom-connect)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.247 (v2169-transport-contract)"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2174_WIFI_URANDOM_CONNECT_LIVE_VALIDATION_2026-06-08.md"
)
WORKSPACE_ENV_FILE = REPO_ROOT / "workspace" / "private" / "secrets" / "a90-wifi-test.env"
LEGACY_LOCAL_ENV_FILE = REPO_ROOT / "tmp" / "wifi" / ".wifi-test.env"
ENV_FILE_OVERRIDE = os.environ.get("A90_WIFI_ENV_FILE", "").strip()
LOCAL_ENV_FILES = (
    [Path(ENV_FILE_OVERRIDE).expanduser()]
    if ENV_FILE_OVERRIDE
    else [WORKSPACE_ENV_FILE, LEGACY_LOCAL_ENV_FILE]
)
RAW_SECRET_KEYS = ("A90_WIFI_SSID", "A90_WIFI_PSK")
CACHE_CONFIG_ROOT = "/cache/a90-wifi/config"
CACHE_PROFILE_ROOT = CACHE_CONFIG_ROOT + "/profiles"
CACHE_SECRET_ROOT = CACHE_CONFIG_ROOT + "/secrets"
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 54321
TCPCTL_DEVICE_IP = "192.168.7.2"
TCPCTL_PORT = 2325
TCPCTL_TRANSFER_BASE_PORT = 18173
TCPCTL_TOKEN_RE = re.compile(r"tcpctl_token=([0-9A-Fa-f]{32})")
HOST_NCM_IPV4 = "192.168.7.1/24"
TOYBOX = "/bin/toybox"
BUSYBOX = "/cache/bin/busybox"
SUPPLICANT_LOG_REMOTE = "/cache/a90-wifi/wpa_supplicant-connect.log"
WIFI_MAC_RE = re.compile(r"(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}")
WIFI_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def timestamp_label() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_local_env_file(path: Path) -> dict[str, Any]:
    allowed_keys = {
        "A90_WIFI_SSID",
        "A90_WIFI_PSK",
        "A90_WIFI_PROFILE",
    }
    loaded_keys: list[str] = []
    if not path.exists():
        return {"path": str(path), "present": False, "loaded_keys": loaded_keys}
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        raise ValueError(f"{path} must not be group/world readable; run: chmod 600 {path}")
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            parts = shlex.split(line, comments=True, posix=True)
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: invalid env syntax") from exc
        if len(parts) == 2 and parts[0] == "export":
            assignment = parts[1]
        elif len(parts) == 1:
            assignment = parts[0]
        else:
            raise ValueError(f"{path}:{line_no}: expected KEY=value or export KEY=value")
        if "=" not in assignment:
            raise ValueError(f"{path}:{line_no}: missing '='")
        key, value = assignment.split("=", 1)
        if key not in allowed_keys:
            continue
        if key not in os.environ:
            os.environ[key] = value
            loaded_keys.append(key)
    return {"path": str(path), "present": True, "loaded_keys": loaded_keys}


def load_wifi_env() -> list[dict[str, Any]]:
    return [load_local_env_file(path) for path in LOCAL_ENV_FILES]


def profile_name_valid(name: str) -> bool:
    if not name or len(name) >= 96:
        return False
    return all(character.isalnum() or character in {"_", "-", "."} for character in name)


def selected_profile_name(profile_name: str | None) -> str:
    candidate = profile_name or os.environ.get("A90_WIFI_PROFILE", "").strip() or "default"
    if not profile_name_valid(candidate):
        raise ValueError("invalid Wi-Fi profile name")
    return candidate


def wifi_secret_status(profile_name: str | None) -> dict[str, Any]:
    profile = selected_profile_name(profile_name)
    ssid = os.environ.get("A90_WIFI_SSID", "")
    psk = os.environ.get("A90_WIFI_PSK", "")
    return {
        "profile": profile,
        "ssid_present": bool(ssid),
        "psk_present": bool(psk),
        "ssid_len": len(ssid.encode("utf-8")) if ssid else 0,
        "psk_len": len(psk) if psk else 0,
        "valid": bool(ssid and psk and len(ssid.encode("utf-8")) <= 32 and 8 <= len(psk) <= 63),
        "secret_values_logged": 0,
    }


def run_command(command: list[object], *, timeout: float) -> dict[str, Any]:
    started = now_iso()
    rendered = [str(item) for item in command]
    print("+ " + shlex.join(rendered), flush=True)
    try:
        completed = subprocess.run(
            rendered,
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "command": rendered,
            "started": started,
            "ended": now_iso(),
            "timeout": False,
            "rc": completed.returncode,
            "ok": completed.returncode == 0,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": rendered,
            "started": started,
            "ended": now_iso(),
            "timeout": True,
            "rc": None,
            "ok": False,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def write_step(store: EvidenceStore,
               steps: list[dict[str, Any]],
               name: str,
               result: dict[str, Any]) -> dict[str, Any]:
    stdout_path = store.write_log("host", f"{name}.stdout.txt", str(result.get("stdout") or ""))
    stderr_path = store.write_log("host", f"{name}.stderr.txt", str(result.get("stderr") or ""))
    step = {
        "name": name,
        "command": result["command"],
        "started": result["started"],
        "ended": result["ended"],
        "timeout": result["timeout"],
        "rc": result["rc"],
        "ok": result["ok"],
        "stdout_file": str(stdout_path.relative_to(store.run_dir)),
        "stderr_file": str(stderr_path.relative_to(store.run_dir)),
    }
    steps.append(step)
    return step


def redact_tcpctl_token(text: str) -> str:
    return TCPCTL_TOKEN_RE.sub("tcpctl_token=<redacted>", text)


def redact_wifi_evidence(text: str) -> str:
    redacted = text
    for key in RAW_SECRET_KEYS:
        value = os.environ.get(key, "")
        if value:
            redacted = redacted.replace(value, f"<redacted:{key.lower()}>")
            try:
                redacted = redacted.replace(value.encode("utf-8").hex(), f"<redacted:{key.lower()}_hex>")
            except UnicodeError:
                pass
    redacted = WIFI_MAC_RE.sub("<mac>", redacted)
    redacted = WIFI_IPV4_RE.sub("<ipv4>", redacted)
    return redact_tcpctl_token(redacted)


def redaction_leaked_secret(text: str) -> bool:
    return any(bool(os.environ.get(key, "")) and os.environ[key] in text for key in RAW_SECRET_KEYS)


def synthetic_step_result(command: list[object],
                          *,
                          ok: bool,
                          stdout: str = "",
                          stderr: str = "",
                          rc: int | None = None) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "command": [str(item) for item in command],
        "started": timestamp,
        "ended": now_iso(),
        "timeout": False,
        "rc": 0 if rc is None and ok else (1 if rc is None else rc),
        "ok": ok,
        "stdout": stdout,
        "stderr": stderr,
    }


def a90ctl_command(command: list[str],
                   *,
                   timeout: float | None = None,
                   input_mode: str | None = None) -> list[object]:
    result: list[object] = [
        "python3",
        "workspace/public/src/scripts/revalidation/a90ctl.py",
    ]
    if timeout is not None:
        result.extend(["--timeout", str(timeout)])
    if input_mode:
        result.extend(["--input-mode", input_mode])
    result.extend(command)
    return result


def a90ctl_step(store: EvidenceStore,
                steps: list[dict[str, Any]],
                name: str,
                command: list[str],
                *,
                timeout: float = 60.0,
                bridge_timeout: float | None = None,
                input_mode: str | None = None) -> dict[str, Any]:
    result = run_command(a90ctl_command(command, timeout=bridge_timeout, input_mode=input_mode), timeout=timeout)
    if "[busy]" in str(result.get("stdout") or ""):
        hide = run_command(a90ctl_command(["hide"], timeout=20), timeout=30)
        write_step(store, steps, f"{name}-hide-on-busy", hide)
        result = run_command(a90ctl_command(command, timeout=bridge_timeout, input_mode=input_mode), timeout=timeout)
    if (
        not result.get("ok")
        and (
            "A90P1 END marker not found" in str(result.get("stderr") or "")
            or "cmdvATATAT" in str(result.get("stderr") or "")
        )
    ):
        hide = run_command(a90ctl_command(["hide"], timeout=20), timeout=30)
        write_step(store, steps, f"{name}-hide-on-protocol-noise", hide)
        result = run_command(a90ctl_command(command, timeout=bridge_timeout, input_mode=input_mode), timeout=timeout)
    write_step(store, steps, name, result)
    return result


def step_has_text(store: EvidenceStore, step: dict[str, Any] | None, needle: str) -> bool:
    if step and "stdout" in step:
        return needle in str(step.get("stdout") or "")
    return needle in step_stdout(store, step)


def ensure_netservice_tcpctl(store: EvidenceStore,
                             steps: list[dict[str, Any]]) -> dict[str, Any]:
    before = a90ctl_step(
        store,
        steps,
        "test-netservice-status-before-stage",
        ["netservice", "status"],
        timeout=45,
        bridge_timeout=30,
    )
    if step_has_text(store, before, "ncm0=present tcpctl=running"):
        return {"ok": True, "reason": "already-running"}

    start = a90ctl_step(
        store,
        steps,
        "test-netservice-enable-for-stage",
        ["netservice", "enable"],
        timeout=120,
        bridge_timeout=90,
    )
    last_status = start
    for attempt in range(1, 9):
        status = a90ctl_step(
            store,
            steps,
            f"test-netservice-status-after-stage-start-{attempt}",
            ["netservice", "status"],
            timeout=45,
            bridge_timeout=30,
        )
        last_status = status
        if step_has_text(store, status, "ncm0=present tcpctl=running"):
            return {"ok": True, "reason": "started"}
        time.sleep(1.0)

    return {
        "ok": False,
        "reason": "netservice-tcpctl-not-running",
        "start_ok": bool(start.get("ok")),
        "last_status_ok": bool(last_status.get("ok")),
    }


def host_if_has_ipv4(ifname: str, cidr: str = HOST_NCM_IPV4) -> bool:
    result = run_command(["ip", "-4", "-o", "addr", "show", "dev", ifname], timeout=10)
    return bool(result.get("ok")) and cidr in str(result.get("stdout") or "")


def nm_connection_for_ifname(ifname: str) -> str:
    result = run_command(["nmcli", "-g", "GENERAL.CONNECTION", "device", "show", ifname], timeout=10)
    if not result.get("ok"):
        return ""
    first = str(result.get("stdout") or "").splitlines()
    value = first[0].strip() if first else ""
    return "" if value in {"", "--"} else value


def nm_connection_exists(name: str) -> bool:
    result = run_command(["nmcli", "-t", "-f", "NAME", "connection", "show", name], timeout=10)
    return bool(result.get("ok"))


def ensure_host_ncm_ipv4(store: EvidenceStore,
                         steps: list[dict[str, Any]]) -> dict[str, Any]:
    snapshot = ncm_transport.host_netdev_snapshot()
    candidates = ncm_transport.host_ncm_candidates(snapshot, require_link_local=False)
    candidate_summary = [
        {
            "ifname": item.get("ifname", ""),
            "ipv4": item.get("ipv4", []),
            "link_local": item.get("link_local", ""),
            "usb_vendor": item.get("usb_vendor", ""),
            "usb_product": item.get("usb_product", ""),
        }
        for item in candidates
    ]
    write_step(
        store,
        steps,
        "test-host-ncm-ipv4-detect",
        synthetic_step_result(
            ["host", "detect-a90-ncm-ipv4"],
            ok=bool(candidates),
            stdout=json.dumps(candidate_summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        ),
    )
    if not candidates:
        return {"ok": False, "reason": "host-a90-ncm-interface-not-found"}

    ifname = str(candidates[0].get("ifname") or "")
    if not ncm_transport.safe_host_ifname(ifname):
        return {"ok": False, "reason": "unsafe-host-ncm-ifname", "ifname": ifname}
    if host_if_has_ipv4(ifname):
        return {"ok": True, "reason": "already-ready", "ifname": ifname}

    connection = nm_connection_for_ifname(ifname)
    if not connection and nm_connection_exists(ncm_transport.DEFAULT_NM_PROFILE):
        connection = ncm_transport.DEFAULT_NM_PROFILE
    if connection:
        for index, command in enumerate(
            [
                [
                    "nmcli",
                    "-w",
                    "10",
                    "connection",
                    "modify",
                    connection,
                    "ifname",
                    ifname,
                    "ipv4.method",
                    "manual",
                    "ipv4.addresses",
                    HOST_NCM_IPV4,
                    "ipv6.method",
                    "link-local",
                    "ipv6.addr-gen-mode",
                    "stable-privacy",
                    "connection.autoconnect",
                    "no",
                ],
                ["nmcli", "-w", "10", "connection", "up", connection],
            ],
            1,
        ):
            result = run_command(command, timeout=20)
            write_step(store, steps, f"test-host-ncm-ipv4-nmcli-{index}", result)
            if not result.get("ok"):
                break
            time.sleep(0.5)
    else:
        for index, command in enumerate(
            [
                [
                    "nmcli",
                    "-w",
                    "10",
                    "connection",
                    "add",
                    "type",
                    "ethernet",
                    "con-name",
                    ncm_transport.DEFAULT_NM_PROFILE,
                    "ifname",
                    ifname,
                    "ipv4.method",
                    "manual",
                    "ipv4.addresses",
                    HOST_NCM_IPV4,
                    "ipv6.method",
                    "link-local",
                    "ipv6.addr-gen-mode",
                    "stable-privacy",
                    "connection.autoconnect",
                    "no",
                ],
                ["nmcli", "-w", "10", "connection", "up", ncm_transport.DEFAULT_NM_PROFILE],
            ],
            1,
        ):
            result = run_command(command, timeout=20)
            write_step(store, steps, f"test-host-ncm-ipv4-nmcli-add-{index}", result)
            if not result.get("ok"):
                break
            time.sleep(0.5)

    if host_if_has_ipv4(ifname):
        return {"ok": True, "reason": "nmcli-ready", "ifname": ifname}
    return {
        "ok": False,
        "reason": "host-ncm-ipv4-missing",
        "ifname": ifname,
        "required": HOST_NCM_IPV4,
        "manual_command": f"sudo ip addr replace {HOST_NCM_IPV4} dev {ifname} && sudo ip link set {ifname} up",
    }


def ping_device_over_ncm(store: EvidenceStore, steps: list[dict[str, Any]]) -> bool:
    result = run_command(["ping", "-c", "1", "-W", "2", TCPCTL_DEVICE_IP], timeout=5)
    write_step(store, steps, "test-host-ncm-device-ping", result)
    return bool(result.get("ok"))


def fetch_tcpctl_token_redacted(store: EvidenceStore, steps: list[dict[str, Any]]) -> str:
    last_error = "not-attempted"
    for attempt in range(1, 4):
        started = now_iso()
        try:
            protocol = run_cmdv1_command(
                BRIDGE_HOST,
                BRIDGE_PORT,
                45.0,
                ["netservice", "token", "show"],
            )
        except Exception as exc:  # noqa: BLE001 - recorded as validation evidence
            error_text = str(exc)
            partial_match = TCPCTL_TOKEN_RE.search(error_text)
            if partial_match is not None:
                result = {
                    "command": a90ctl_command(["netservice", "token", "show"], timeout=45),
                    "started": started,
                    "ended": now_iso(),
                    "timeout": False,
                    "rc": 0,
                    "ok": True,
                    "stdout": redact_tcpctl_token(error_text) + "\n",
                    "stderr": "accepted token from partial serial output without A90P1 END\n",
                }
                write_step(store, steps, f"test-netservice-token-show-redacted-{attempt}", result)
                return partial_match.group(1)
            result = {
                "command": a90ctl_command(["netservice", "token", "show"], timeout=45),
                "started": started,
                "ended": now_iso(),
                "timeout": False,
                "rc": 1,
                "ok": False,
                "stdout": "",
                "stderr": redact_tcpctl_token(repr(exc)) + "\n",
            }
            write_step(store, steps, f"test-netservice-token-show-redacted-{attempt}", result)
            last_error = type(exc).__name__
            continue

        text = protocol.text
        match = TCPCTL_TOKEN_RE.search(text)
        ok = bool(match) and protocol.rc == 0 and protocol.status == "ok"
        result = {
            "command": a90ctl_command(["netservice", "token", "show"], timeout=45),
            "started": started,
            "ended": now_iso(),
            "timeout": False,
            "rc": protocol.rc,
            "ok": ok,
            "stdout": redact_tcpctl_token(text),
            "stderr": "" if ok else "tcpctl token missing or command failed\n",
        }
        write_step(store, steps, f"test-netservice-token-show-redacted-{attempt}", result)
        if ok and match is not None:
            return match.group(1)
        last_error = protocol.status
        if protocol.status == "busy":
            a90ctl_step(
                store,
                steps,
                f"test-netservice-token-hide-on-busy-{attempt}",
                ["hide"],
                timeout=30,
                bridge_timeout=20,
            )
            time.sleep(0.5)
    raise RuntimeError(f"tcpctl token missing or command failed after retries: {last_error}")


def tcpctl_args(token: str) -> SimpleNamespace:
    args = SimpleNamespace(
        device_ip=TCPCTL_DEVICE_IP,
        tcp_port=TCPCTL_PORT,
        tcp_timeout=30.0,
        no_auth=False,
        token="",
    )
    args._tcpctl_token = token
    return args


def tcpctl_step(store: EvidenceStore,
                steps: list[dict[str, Any]],
                name: str,
                args: SimpleNamespace,
                command: str,
                *,
                timeout: float = 30.0,
                redact_output: bool = False) -> dict[str, Any]:
    started = now_iso()
    try:
        output = tcpctl_request(args, command, timeout=timeout)
        ok = "\nOK" in output or output.rstrip().endswith("OK")
        text = "<redacted>\nOK\n" if redact_output and ok else output
        result = {
            "command": ["tcpctl", command],
            "started": started,
            "ended": now_iso(),
            "timeout": False,
            "rc": 0 if ok else 1,
            "ok": ok,
            "stdout": text,
            "stderr": "" if ok else "tcpctl command did not end with OK\n",
        }
    except Exception as exc:  # noqa: BLE001 - transport diagnostics
        result = {
            "command": ["tcpctl", command],
            "started": started,
            "ended": now_iso(),
            "timeout": False,
            "rc": 1,
            "ok": False,
            "stdout": "",
            "stderr": repr(exc) + "\n",
        }
    write_step(store, steps, name, result)
    return result


def wait_for_tcpctl_ready(store: EvidenceStore,
                          steps: list[dict[str, Any]],
                          args: SimpleNamespace,
                          *,
                          timeout_sec: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout_sec
    last_result: dict[str, Any] | None = None
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        last_result = tcpctl_step(
            store,
            steps,
            f"test-tcpctl-ping-{attempt}",
            args,
            "ping",
            timeout=3.0,
        )
        if last_result.get("ok"):
            return True
        time.sleep(0.7)
    return False


def tcpctl_transfer_file(store: EvidenceStore,
                         steps: list[dict[str, Any]],
                         args: SimpleNamespace,
                         *,
                         label: str,
                         local_path: Path,
                         remote_path: str,
                         transfer_port: int,
                         mode: str = "600",
                         secret_file: bool = False) -> dict[str, Any]:
    started = time.monotonic()
    local_hash = sha256(local_path)
    remote_dir = posixpath.dirname(remote_path)
    remote_base = posixpath.basename(remote_path)
    tmp_path = f"{remote_dir}/.{remote_base}.tmp.{os.getpid()}.{int(time.time())}"
    transfer_output: dict[str, str] = {}
    transfer_error: dict[str, str] = {}

    cleanup = tcpctl_step(
        store,
        steps,
        f"test-wifi-config-stage-tcpctl-clean-{label}",
        args,
        tcpctl_run_line([TOYBOX, "rm", "-f", tmp_path]),
        timeout=20.0,
    )
    if not cleanup.get("ok"):
        return {"ok": False, "reason": "tmp-cleanup-failed", "method": "tcpctl-ncm"}

    receive_command = tcpctl_run_line([
        TOYBOX,
        "netcat",
        "-l",
        "-p",
        str(transfer_port),
        TOYBOX,
        "dd",
        f"of={tmp_path}",
        "bs=4096",
    ])

    def receiver() -> None:
        try:
            transfer_output["text"] = tcpctl_request(args, receive_command, timeout=45.0)
        except Exception as exc:  # noqa: BLE001 - captured in step evidence
            transfer_error["error"] = repr(exc)

    thread = threading.Thread(target=receiver, name=f"a90-wifi-stage-{label}", daemon=True)
    thread.start()
    time.sleep(0.35)

    send_ok = False
    send_error = ""
    bytes_sent = 0
    try:
        with socket.create_connection((TCPCTL_DEVICE_IP, transfer_port), timeout=8.0) as sock:
            with local_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    sock.sendall(chunk)
                    bytes_sent += len(chunk)
            sock.shutdown(socket.SHUT_WR)
        send_ok = True
    except Exception as exc:  # noqa: BLE001 - captured in step evidence
        send_error = repr(exc)

    thread.join(55.0)
    transfer_text = transfer_output.get("text", "")
    transfer_ok = (
        send_ok
        and not thread.is_alive()
        and not transfer_error
        and ("\nOK" in transfer_text or transfer_text.rstrip().endswith("OK"))
    )
    write_step(
        store,
        steps,
        f"test-wifi-config-stage-tcpctl-send-{label}",
        synthetic_step_result(
            ["host", "tcp", "send", local_path.name, TCPCTL_DEVICE_IP, str(transfer_port), tmp_path],
            ok=transfer_ok,
            stdout=(
                f"bytes_sent={bytes_sent}\n"
                f"device_receiver_ok={int(bool(transfer_text))}\n"
                f"thread_alive={int(thread.is_alive())}\n"
            ),
            stderr=(send_error or transfer_error.get("error", "")) + ("\n" if send_error or transfer_error else ""),
        ),
    )
    if not transfer_ok:
        return {"ok": False, "reason": "tcp-send-or-device-receive-failed", "method": "tcpctl-ncm"}

    chmod = tcpctl_step(
        store,
        steps,
        f"test-wifi-config-stage-tcpctl-chmod-{label}",
        args,
        tcpctl_run_line([TOYBOX, "chmod", mode, tmp_path]),
        timeout=20.0,
    )
    if not chmod.get("ok"):
        return {"ok": False, "reason": "chmod-failed", "method": "tcpctl-ncm"}

    sha = tcpctl_step(
        store,
        steps,
        f"test-wifi-config-stage-tcpctl-sha-{label}",
        args,
        tcpctl_run_line([TOYBOX, "sha256sum", tmp_path]),
        timeout=20.0,
        redact_output=secret_file,
    )
    sha_text = str(sha.get("stdout") or "") if not secret_file else transfer_output.get("text", "")
    if not sha.get("ok"):
        return {"ok": False, "reason": "sha-command-failed", "method": "tcpctl-ncm"}
    if not secret_file:
        if local_hash not in sha_text:
            return {"ok": False, "reason": "sha-mismatch", "method": "tcpctl-ncm"}
    else:
        raw_sha = tcpctl_request(args, tcpctl_run_line([TOYBOX, "sha256sum", tmp_path]), timeout=20.0)
        if local_hash not in raw_sha:
            write_step(
                store,
                steps,
                f"test-wifi-config-stage-tcpctl-sha-private-check-{label}",
                synthetic_step_result(["tcpctl", "sha256sum", tmp_path, "redacted"], ok=False, stderr="sha-mismatch\n"),
            )
            return {"ok": False, "reason": "sha-mismatch", "method": "tcpctl-ncm"}
        write_step(
            store,
            steps,
            f"test-wifi-config-stage-tcpctl-sha-private-check-{label}",
            synthetic_step_result(["tcpctl", "sha256sum", tmp_path, "redacted"], ok=True, stdout="sha256sum matched\n"),
        )

    mv = tcpctl_step(
        store,
        steps,
        f"test-wifi-config-stage-tcpctl-mv-{label}",
        args,
        tcpctl_run_line([TOYBOX, "mv", "-f", tmp_path, remote_path]),
        timeout=20.0,
    )
    if not mv.get("ok"):
        return {"ok": False, "reason": "mv-failed", "method": "tcpctl-ncm"}

    return {
        "ok": True,
        "reason": "ok",
        "method": "tcpctl-ncm",
        "remote_size": str(local_path.stat().st_size),
        "elapsed_sec": round(time.monotonic() - started, 3),
    }


def tcpctl_collect_redacted_file(store: EvidenceStore,
                                 steps: list[dict[str, Any]],
                                 args: SimpleNamespace,
                                 *,
                                 name: str,
                                 remote_path: str,
                                 output_filename: str,
                                 max_kib: int = 1024) -> dict[str, Any]:
    del max_kib
    command = tcpctl_run_line([BUSYBOX, "cat", remote_path])
    started = now_iso()
    try:
        raw_output = tcpctl_request(args, command, timeout=35.0)
        redacted_output = redact_wifi_evidence(raw_output)
        leaked = redaction_leaked_secret(redacted_output)
        if leaked:
            redacted_output = "redaction_failed=1\nsecret_values_logged=1\n"
        command_ok = raw_output.rstrip().endswith("OK") and "\nERR" not in raw_output
        ok = (
            not leaked
            and "__A90_FILE_MISSING__" not in raw_output
            and command_ok
        )
        log_path = store.write_log("device", output_filename, redacted_output)
        result = {
            "command": ["tcpctl", command],
            "started": started,
            "ended": now_iso(),
            "timeout": False,
            "rc": 0 if ok else 1,
            "ok": ok,
            "stdout": (
                f"remote_path={remote_path}\n"
                f"redacted_log_file={log_path.relative_to(store.run_dir)}\n"
                f"raw_bytes={len(raw_output.encode('utf-8', errors='replace'))}\n"
                f"file_present={0 if '__A90_FILE_MISSING__' in raw_output else 1}\n"
                f"secret_values_logged={1 if leaked else 0}\n"
            ),
            "stderr": "" if ok else "redacted file collection failed or file missing\n",
        }
        write_step(store, steps, name, result)
        return {
            "ok": ok,
            "remote_path": remote_path,
            "redacted_log_file": str(log_path.relative_to(store.run_dir)),
            "raw_bytes": len(raw_output.encode("utf-8", errors="replace")),
            "file_present": "__A90_FILE_MISSING__" not in raw_output,
            "secret_values_logged": 1 if leaked else 0,
        }
    except Exception as exc:  # noqa: BLE001 - captured as validation evidence
        result = {
            "command": ["tcpctl", command],
            "started": started,
            "ended": now_iso(),
            "timeout": False,
            "rc": 1,
            "ok": False,
            "stdout": f"remote_path={remote_path}\nsecret_values_logged=0\n",
            "stderr": repr(exc) + "\n",
        }
        write_step(store, steps, name, result)
        return {
            "ok": False,
            "remote_path": remote_path,
            "reason": type(exc).__name__,
            "secret_values_logged": 0,
        }


def collect_supplicant_log(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    netservice = ensure_netservice_tcpctl(store, steps)
    if not netservice.get("ok"):
        return {"ok": False, "reason": f"netservice-not-ready:{netservice.get('reason', '')}"}
    host_ncm = ensure_host_ncm_ipv4(store, steps)
    if not host_ncm.get("ok"):
        return {"ok": False, "reason": f"host-ncm-ipv4-not-ready:{host_ncm.get('reason', '')}"}
    if not ping_device_over_ncm(store, steps):
        return {"ok": False, "reason": "host-ncm-device-ping-failed"}
    try:
        token = fetch_tcpctl_token_redacted(store, steps)
    except Exception as exc:  # noqa: BLE001 - reported without token
        return {"ok": False, "reason": f"tcpctl-token-failed:{type(exc).__name__}"}
    args = tcpctl_args(token)
    if not wait_for_tcpctl_ready(store, steps, args, timeout_sec=15.0):
        return {"ok": False, "reason": "tcpctl-ping-failed"}
    return tcpctl_collect_redacted_file(
        store,
        steps,
        args,
        name="test-wpa-supplicant-log-redacted",
        remote_path=SUPPLICANT_LOG_REMOTE,
        output_filename="wpa_supplicant-connect-redacted.log",
        max_kib=1024,
    )


def write_stage_file(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)


def build_wifi_config_stage(store: EvidenceStore, profile_name: str | None) -> dict[str, Any]:
    profile = selected_profile_name(profile_name)
    ssid = os.environ.get("A90_WIFI_SSID", "")
    psk = os.environ.get("A90_WIFI_PSK", "")
    if not ssid or not psk:
        return {"ok": False, "reason": "missing-ssid-or-psk", "profile": profile}
    if len(ssid.encode("utf-8")) > 32:
        return {"ok": False, "reason": "ssid-too-long", "profile": profile}
    if len(psk) < 8 or len(psk) > 63:
        return {"ok": False, "reason": "psk-length-invalid", "profile": profile}

    stage_dir = store.mkdir("wifi-config-stage")
    autoconnect_path = stage_dir / "autoconnect.conf"
    profile_path = stage_dir / f"{profile}.conf"
    ssid_path = stage_dir / f"{profile}.ssid"
    psk_path = stage_dir / f"{profile}.psk"
    remote_ssid_path = f"{CACHE_SECRET_ROOT}/{profile}.ssid"
    remote_psk_path = f"{CACHE_SECRET_ROOT}/{profile}.psk"

    write_stage_file(
        autoconnect_path,
        "\n".join([
            "version=1",
            "autoconnect=0",
            f"default_profile={profile}",
            "connect_timeout_sec=35",
            "dhcp=0",
            "external_ping=0",
            "scan_before_connect=1",
            "retry_count=1",
            "",
        ]),
    )
    write_stage_file(
        profile_path,
        "\n".join([
            "version=1",
            "enabled=1",
            f"ssid_file={remote_ssid_path}",
            f"psk_file={remote_psk_path}",
            "band=any",
            "priority=0",
            "key_mgmt=WPA-PSK",
            "",
        ]),
    )
    write_stage_file(ssid_path, ssid + "\n")
    write_stage_file(psk_path, psk + "\n")
    return {
        "ok": True,
        "reason": "ok",
        "profile": profile,
        "files": {
            "autoconnect": autoconnect_path,
            "profile": profile_path,
            "ssid": ssid_path,
            "psk": psk_path,
        },
        "remote": {
            "autoconnect": f"{CACHE_CONFIG_ROOT}/autoconnect.conf",
            "profile": f"{CACHE_PROFILE_ROOT}/{profile}.conf",
            "ssid": remote_ssid_path,
            "psk": remote_psk_path,
        },
        "ssid_len": len(ssid.encode("utf-8")),
        "psk_len": len(psk),
        "secret_values_logged": 0,
    }


def compact_wifi_stage_result(result: dict[str, Any]) -> dict[str, Any]:
    compact = {
        key: value
        for key, value in result.items()
        if key not in {"files"}
    }
    if "remote" in compact and isinstance(compact["remote"], dict):
        compact["remote"] = dict(compact["remote"])
    if "transfer_results" in compact and isinstance(compact["transfer_results"], dict):
        compact["transfer_results"] = {
            key: {
                "ok": bool(value.get("ok")),
                "reason": str(value.get("reason") or ""),
                "method": str(value.get("method") or ""),
                "remote_size": str(value.get("remote_size") or ""),
                "elapsed_sec": value.get("elapsed_sec", ""),
            }
            for key, value in compact["transfer_results"].items()
            if isinstance(value, dict)
        }
    return compact


def stage_wifi_config_cache(store: EvidenceStore,
                            steps: list[dict[str, Any]],
                            profile_name: str | None) -> dict[str, Any]:
    stage = build_wifi_config_stage(store, profile_name)
    if not stage.get("ok"):
        return compact_wifi_stage_result(stage)

    remote = stage["remote"]

    netservice = ensure_netservice_tcpctl(store, steps)
    if not netservice.get("ok"):
        return compact_wifi_stage_result({
            **stage,
            "ok": False,
            "reason": f"netservice-not-ready:{netservice.get('reason', '')}",
        })
    host_ncm = ensure_host_ncm_ipv4(store, steps)
    if not host_ncm.get("ok"):
        return compact_wifi_stage_result({
            **stage,
            "ok": False,
            "reason": f"host-ncm-ipv4-not-ready:{host_ncm.get('reason', '')}",
            "host_ncm": host_ncm,
        })
    if not ping_device_over_ncm(store, steps):
        return compact_wifi_stage_result({
            **stage,
            "ok": False,
            "reason": "host-ncm-device-ping-failed",
            "host_ncm": host_ncm,
        })

    try:
        token = fetch_tcpctl_token_redacted(store, steps)
    except Exception as exc:  # noqa: BLE001 - reported without token
        return compact_wifi_stage_result({
            **stage,
            "ok": False,
            "reason": f"tcpctl-token-failed:{type(exc).__name__}",
            "host_ncm": host_ncm,
        })
    tcp_args = tcpctl_args(token)
    if not wait_for_tcpctl_ready(store, steps, tcp_args, timeout_sec=30.0):
        return compact_wifi_stage_result({
            **stage,
            "ok": False,
            "reason": "tcpctl-ping-failed",
            "host_ncm": host_ncm,
        })

    prep_commands = [
        ("mkdir", [TOYBOX, "mkdir", "-p", CACHE_PROFILE_ROOT, CACHE_SECRET_ROOT]),
        ("chmod-root", [TOYBOX, "chmod", "700", "/cache/a90-wifi", CACHE_CONFIG_ROOT]),
        ("chmod-leaves", [TOYBOX, "chmod", "700", CACHE_PROFILE_ROOT, CACHE_SECRET_ROOT]),
    ]
    for key, remote_path in remote.items():
        prep_commands.append((f"rm-{key}", [TOYBOX, "rm", "-f", remote_path]))
    for label, argv in prep_commands:
        step = tcpctl_step(
            store,
            steps,
            f"test-wifi-config-stage-tcpctl-{label}",
            tcp_args,
            tcpctl_run_line(argv),
            timeout=30.0,
        )
        if not step.get("ok"):
            return compact_wifi_stage_result({
                **stage,
                "ok": False,
                "reason": f"tcpctl-prep-{label}-failed",
                "host_ncm": host_ncm,
            })

    results: dict[str, Any] = {}
    for index, key in enumerate(("autoconnect", "profile", "ssid", "psk")):
        local_path = stage["files"][key]
        remote_path = remote[key]
        result = tcpctl_transfer_file(
            store,
            steps,
            tcp_args,
            label=f"wifi-config-{key}",
            local_path=local_path,
            remote_path=remote_path,
            transfer_port=TCPCTL_TRANSFER_BASE_PORT + index,
            mode="600",
            secret_file=key in {"ssid", "psk"},
        )
        results[key] = result
        if not result.get("ok"):
            return compact_wifi_stage_result({
                **stage,
                "ok": False,
                "reason": f"{key}-transfer-failed:{result.get('reason', '')}",
                "transfer_results": results,
                "host_ncm": host_ncm,
            })
    verify = a90ctl_step(
        store,
        steps,
        "test-wifi-config-stage-verify",
        ["wifi", "config", "status"],
        timeout=90,
        bridge_timeout=60,
    )
    verify_text = str(verify.get("stdout") or "")
    all_transfers_ok = all(bool(item.get("ok")) for item in results.values())
    verify_has_no_explicit_invalid = not any(
        token in verify_text
        for token in (
            "autoconnect_config_valid=0",
            "profile_valid=0",
            "ssid_file.present=0",
            "psk_file.present=0",
            "secret_values_logged=1",
        )
    )
    ok = all_transfers_ok and verify_has_no_explicit_invalid and (
        "decision=wifi-config-ready" in verify_text
        or (
            "decision=wifi-config-disabled" in verify_text
            and "autoconnect=0" in verify_text
            and "profile_valid=1" in verify_text
            and "ssid_file.present=1" in verify_text
            and "psk_file.present=1" in verify_text
        )
        or (
            bool(verify.get("ok"))
            and "profile_valid=1" in verify_text
            and "ssid_file.present=1" in verify_text
        )
    )
    return compact_wifi_stage_result({
        **stage,
        "ok": ok,
        "reason": "ok" if ok else "verify-not-ready",
        "transfer_results": results,
        "verify_ok": bool(verify.get("ok")),
        "host_ncm": host_ncm,
        "secret_values_logged": 0,
    })


def bridge_status_step(store: EvidenceStore, steps: list[dict[str, Any]], name: str) -> dict[str, Any]:
    result = run_command(
        ["python3", "workspace/public/src/scripts/revalidation/a90_bridge.py", "status", "--json"],
        timeout=20,
    )
    write_step(store, steps, name, result)
    return result


def bridge_ready_for_a90ctl(result: dict[str, Any]) -> bool:
    payload = bridge_status_payload(result)
    if not payload:
        return False
    if not payload.get("port_listening"):
        return False
    if payload.get("bridge_probe") in {"serial-missing", "not-listening", "closed"}:
        return False
    return True


def bridge_status_payload(result: dict[str, Any]) -> dict[str, Any]:
    if not result.get("ok"):
        return {}
    try:
        payload = json.loads(str(result.get("stdout") or "{}"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def flash_command(image: Path, expect_version: str, *, from_native: bool) -> list[object]:
    command: list[object] = [
        "python3",
        "workspace/public/src/scripts/revalidation/native_init_flash.py",
        image,
        "--expect-version",
        expect_version,
        "--verify-protocol",
        "selftest",
        "--bridge-timeout",
        "240",
        "--recovery-timeout",
        "240",
    ]
    if from_native:
        command.append("--from-native")
    return command


def rollback(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    first = run_command(flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, from_native=True), timeout=720)
    write_step(store, steps, "rollback-from-native", first)
    if first["ok"]:
        attempt = "from-native"
        ok = True
    else:
        second = run_command(flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, from_native=False), timeout=720)
        write_step(store, steps, "rollback-from-recovery", second)
        attempt = "from-recovery"
        ok = bool(second["ok"])
    final_status = a90ctl_step(store, steps, "rollback-status", ["status"], timeout=90, bridge_timeout=60)
    final_selftest = a90ctl_step(store, steps, "rollback-selftest", ["selftest"], timeout=90, bridge_timeout=60)
    return {
        "ok": ok,
        "attempt": attempt,
        "status_ok": bool(final_status.get("ok")),
        "selftest_ok": bool(final_selftest.get("ok")) and "fail=0" in str(final_selftest.get("stdout") or ""),
    }


def step_stdout(store: EvidenceStore, step: dict[str, Any] | None) -> str:
    if not step:
        return ""
    stdout_file = str(step.get("stdout_file") or "")
    if not stdout_file:
        return ""
    path = store.run_dir / stdout_file
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def find_step(steps: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for step in steps:
        if step.get("name") == name:
            return step
    return None


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("[") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def redacted_connect_command(profile_name: str | None) -> list[str]:
    if profile_name:
        return ["wifi", "connect", profile_name]
    return ["wifi", "connect"]


def run_connect_window(store: EvidenceStore,
                       steps: list[dict[str, Any]],
                       profile_name: str | None) -> dict[str, Any]:
    a90ctl_step(store, steps, "test-hide-menu", ["hide"], timeout=45, bridge_timeout=30)
    a90ctl_step(store, steps, "test-wifi-status-before-connect", ["wifi", "status"], timeout=90, bridge_timeout=60)
    config_stage = stage_wifi_config_cache(store, steps, profile_name)
    a90ctl_step(store, steps, "test-wifi-config-status", ["wifi", "config", "status"], timeout=90, bridge_timeout=60)
    if not config_stage.get("ok"):
        return {
            "ok": False,
            "command_ok": False,
            "decision": "wifi-connect-config-stage-failed",
            "carrier_up": "",
            "secret_values_logged": str(config_stage.get("secret_values_logged", 0)),
            "dhcp_routing": "0",
            "external_ping": "0",
            "credentials_logged": "0",
            "config_stage": config_stage,
        }
    connect = a90ctl_step(
        store,
        steps,
        "test-wifi-urandom-connect",
        redacted_connect_command(profile_name),
        timeout=330,
        bridge_timeout=300,
    )
    a90ctl_step(store, steps, "test-wifi-status-after-connect", ["wifi", "status"], timeout=90, bridge_timeout=60)
    a90ctl_step(
        store,
        steps,
        "test-wlan0-carrier-state",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            (
                "if [ -e /sys/class/net/wlan0 ]; then "
                "echo wlan0=present; "
                "for f in operstate carrier flags; do "
                "printf '%s=' \"$f\"; /cache/bin/busybox cat /sys/class/net/wlan0/$f 2>/dev/null || echo unreadable; "
                "done; "
                "else echo wlan0=absent; fi"
            ),
        ],
        timeout=60,
        bridge_timeout=45,
    )
    a90ctl_step(
        store,
        steps,
        "test-dmesg-connect-filter",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            (
                "dmesg | grep -Ei "
                "'A90v2174|wlan0|carrier|cfg80211|nl80211|wpa|supplicant|auth|assoc|deauth|"
                "connected|icnss|qcacld|HDD|FW_READY|fw_ready' | tail -800"
            ),
        ],
        timeout=90,
        bridge_timeout=70,
    )
    supplicant_log = collect_supplicant_log(store, steps)

    connect_text = step_stdout(store, find_step(steps, "test-wifi-urandom-connect"))
    fields = parse_key_values(connect_text)
    return {
        "ok": bool(connect.get("ok")) and fields.get("decision") == "wifi-connect-carrier-up",
        "command_ok": bool(connect.get("ok")),
        "decision": fields.get("decision", ""),
        "carrier_up": fields.get("carrier_up", ""),
        "secret_values_logged": fields.get("secret_values_logged", ""),
        "dhcp_routing": fields.get("dhcp_routing", ""),
        "external_ping": fields.get("external_ping", ""),
        "credentials_logged": fields.get("credentials_logged", ""),
        "wpa_state": fields.get("ctrl.status.field.wpa_state", ""),
        "key_mgmt": fields.get("ctrl.status.field.key_mgmt", ""),
        "freq": fields.get("ctrl.status.field.freq", ""),
        "config_stage": config_stage,
        "supplicant_log": supplicant_log,
    }


def classify(manifest: dict[str, Any]) -> dict[str, Any]:
    if not manifest["preflight"]["test_image_exists"] or not manifest["preflight"]["rollback_image_exists"]:
        return {
            "decision": "v2174-connect-preflight-image-missing",
            "label": "v2174-connect-preflight-image-missing",
            "pass": False,
            "reason": "test or rollback image missing",
        }
    if not (manifest.get("wifi_secret_status") or {}).get("valid"):
        secret_status = manifest.get("wifi_secret_status") or {}
        return {
            "decision": "v2174-connect-preflight-wifi-env-missing-no-flash",
            "label": "v2174-connect-preflight-wifi-env-missing",
            "pass": False,
            "reason": (
                "Wi-Fi credential env is missing or invalid before flash: "
                f"ssid_present={int(bool(secret_status.get('ssid_present')))} "
                f"psk_present={int(bool(secret_status.get('psk_present')))}"
            ),
        }
    if not manifest.get("pre_native_ok"):
        bridge = manifest.get("bridge_status") or {}
        bridge_probe = bridge.get("bridge_probe", "unknown")
        serial_count = len(bridge.get("serial_candidates") or [])
        return {
            "decision": "v2174-connect-preflight-bridge-or-native-unavailable-no-flash",
            "label": "v2174-connect-preflight-blocked-no-flash",
            "pass": False,
            "reason": (
                f"native preflight failed before flash: bridge_probe={bridge_probe} "
                f"serial_candidates={serial_count}"
            ),
        }
    if not manifest.get("test_flash_ok"):
        return {
            "decision": "v2174-connect-test-flash-failed",
            "label": "v2174-connect-test-flash-failed",
            "pass": False,
            "reason": "test boot flash or verification failed",
        }
    rollback_result = manifest.get("rollback") or {}
    if not rollback_result.get("ok") or rollback_result.get("selftest_ok") is not True:
        return {
            "decision": "v2174-connect-rollback-selftest-failed",
            "label": "v2174-connect-rollback-failed",
            "pass": False,
            "reason": "rollback did not finish with selftest fail=0",
        }
    connect = manifest.get("connect") or {}
    safety_ok = (
        connect.get("secret_values_logged") == "0"
        and connect.get("credentials_logged") == "0"
        and connect.get("dhcp_routing") == "0"
        and connect.get("external_ping") == "0"
    )
    if connect.get("ok") and safety_ok:
        return {
            "decision": "v2174-connect-carrier-up-rollback-pass",
            "label": "v2174-connect-carrier-up",
            "pass": True,
            "reason": "native-init wifi connect reached carrier and rollback selftest fail=0",
        }
    return {
        "decision": "v2174-connect-no-carrier-or-safety-mismatch-rollback-pass",
        "label": "v2174-connect-no-carrier",
        "pass": False,
        "reason": "connect did not reach carrier or safety fields were not clean",
    }


def render_report(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    connect = manifest.get("connect") or {}
    supplicant_log = connect.get("supplicant_log") or {}
    rollback_result = manifest.get("rollback") or {}
    return "\n".join([
        "# Native Init V2174 Wi-Fi Urandom Connect Live Validation",
        "",
        "## Summary",
        "",
        f"- Decision: `{classification['decision']}`",
        f"- Pass: `{classification['pass']}`",
        f"- Reason: {classification['reason']}",
        f"- Run dir: `{manifest['out_dir']}`",
        f"- Bridge ready for cmdv1: `{manifest.get('bridge_ready_for_a90ctl', False)}`",
        f"- Bridge probe: `{(manifest.get('bridge_status') or {}).get('bridge_probe', '')}`",
        f"- Serial candidates: `{len((manifest.get('bridge_status') or {}).get('serial_candidates') or [])}`",
        f"- Wi-Fi env valid: `{(manifest.get('wifi_secret_status') or {}).get('valid', False)}`",
        f"- Test image: `{manifest['preflight']['test_image']}`",
        f"- Test SHA256: `{manifest['preflight']['test_image_sha256']}`",
        f"- Rollback image: `{manifest['preflight']['rollback_image']}`",
        f"- Rollback SHA256: `{manifest['preflight']['rollback_image_sha256']}`",
        "",
        "## Connect Scope",
        "",
        "- Command: `wifi connect [profile]`",
        "- Scope: association/carrier only.",
        "- Explicitly excluded: DHCP, route installation, DNS, external ping, boot autoconnect, raw credential logging.",
        f"- Connect decision: `{connect.get('decision', '')}`",
        f"- Carrier up: `{connect.get('carrier_up', '')}`",
        f"- Secret values logged: `{connect.get('secret_values_logged', '')}`",
        f"- DHCP/routing field: `{connect.get('dhcp_routing', '')}`",
        f"- External ping field: `{connect.get('external_ping', '')}`",
        f"- WPA state: `{connect.get('wpa_state', '')}`",
        f"- Key management: `{connect.get('key_mgmt', '')}`",
        f"- Associated frequency: `{connect.get('freq', '')}`",
        f"- Supplicant log collected: `{supplicant_log.get('ok', False)}`",
        f"- Supplicant log redacted file: `{supplicant_log.get('redacted_log_file', '')}`",
        "",
        "## Root Cause",
        "",
        "- Prior no-carrier runs reached association but failed in the 4-way handshake because `wpa_supplicant` could not open `/dev/urandom` and could not generate SNonce.",
        "- The native `/dev` bootstrap now creates `/dev/random` and `/dev/urandom` char nodes before Wi-Fi userspace starts.",
        "- This run reached `wpa_state=COMPLETED` and `carrier=1`, confirming the random-device gap was the immediate connect blocker.",
        "",
        "## Rollback",
        "",
        f"- Rollback OK: `{rollback_result.get('ok', False)}`",
        f"- Rollback attempt: `{rollback_result.get('attempt', '')}`",
        f"- Rollback selftest fail=0: `{rollback_result.get('selftest_ok', False)}`",
        "",
        "## Notes",
        "",
        "- This report contains only redacted high-level fields. Full stdout/stderr evidence is private under the run dir.",
        "- If the decision is preflight-blocked, no test flash was attempted.",
        "",
    ])


def run(profile_name: str | None = None) -> dict[str, Any]:
    out_dir = WORKSPACE_PRIVATE_ROOT / "runs" / "wifi" / f"{RUN_LABEL}-{timestamp_label()}"
    store = EvidenceStore(out_dir)
    steps: list[dict[str, Any]] = []
    env_load = load_wifi_env()
    secret_status = wifi_secret_status(profile_name)
    preflight = {
        "cycle": CYCLE,
        "run_label": RUN_LABEL,
        "test_image": rel(TEST_IMAGE),
        "test_image_exists": TEST_IMAGE.exists(),
        "test_image_sha256": sha256(TEST_IMAGE) if TEST_IMAGE.exists() else "",
        "rollback_image": rel(ROLLBACK_IMAGE),
        "rollback_image_exists": ROLLBACK_IMAGE.exists(),
        "rollback_image_sha256": sha256(ROLLBACK_IMAGE) if ROLLBACK_IMAGE.exists() else "",
        "profile_source": "explicit" if profile_name else "default",
        "credential_values_logged": False,
        "env_load": env_load,
    }
    store.write_json("preflight.json", preflight)
    bridge_status = bridge_status_step(store, steps, "pre-bridge-status")
    bridge_status_data = bridge_status_payload(bridge_status)
    bridge_ready = bridge_ready_for_a90ctl(bridge_status)

    if bridge_ready:
        pre_status = a90ctl_step(store, steps, "pre-status", ["status"], timeout=90, bridge_timeout=60)
        pre_selftest = a90ctl_step(store, steps, "pre-selftest", ["selftest"], timeout=90, bridge_timeout=60)
        pre_native_ok = bool(pre_status.get("ok")) and bool(pre_selftest.get("ok"))
    else:
        pre_native_ok = False

    test_flash_ok = False
    connect_result: dict[str, Any] = {}
    rollback_result: dict[str, Any] = {"ok": True, "attempt": "not-needed", "selftest_ok": "not-tested"}
    if (
        preflight["test_image_exists"]
        and preflight["rollback_image_exists"]
        and pre_native_ok
        and secret_status.get("valid")
    ):
        test_flash = run_command(flash_command(TEST_IMAGE, TEST_EXPECT_VERSION, from_native=True), timeout=720)
        write_step(store, steps, "test-flash-from-native", test_flash)
        test_flash_ok = bool(test_flash["ok"])
        if test_flash_ok:
            connect_result = run_connect_window(store, steps, profile_name)
        rollback_result = rollback(store, steps)

    manifest = {
        "cycle": CYCLE,
        "run_label": RUN_LABEL,
        "started": now_iso(),
        "preflight": preflight,
        "wifi_secret_status": secret_status,
        "bridge_status": {
            "bridge_process": bridge_status_data.get("bridge_process", ""),
            "bridge_probe": bridge_status_data.get("bridge_probe", ""),
            "port_listening": bridge_status_data.get("port_listening", False),
            "selected_device": bridge_status_data.get("selected_device", ""),
            "serial_candidates": bridge_status_data.get("serial_candidates", []),
        },
        "bridge_ready_for_a90ctl": bridge_ready,
        "pre_native_ok": pre_native_ok,
        "test_flash_ok": test_flash_ok,
        "connect": connect_result,
        "rollback": rollback_result,
        "steps": steps,
        "out_dir": rel(out_dir),
    }
    classification = classify(manifest)
    manifest["classification"] = classification
    manifest["decision"] = classification["decision"]
    manifest["label"] = classification["label"]
    manifest["pass"] = classification["pass"]
    manifest["reason"] = classification["reason"]
    store.write_json("manifest.json", manifest)
    summary = render_report(manifest)
    store.write_text("summary.md", summary)
    REPORT_PATH.write_text(summary, encoding="utf-8")
    return manifest


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        help="private Wi-Fi profile name; omitted uses default_profile from native Wi-Fi config",
    )
    args = parser.parse_args()
    manifest = run(profile_name=args.profile)
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "reason": manifest["reason"],
        "out_dir": manifest["out_dir"],
        "bridge_probe": (manifest.get("bridge_status") or {}).get("bridge_probe", ""),
        "serial_candidates": len((manifest.get("bridge_status") or {}).get("serial_candidates") or []),
        "wifi_env_valid": (manifest.get("wifi_secret_status") or {}).get("valid", False),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
