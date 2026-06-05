#!/usr/bin/env python3
"""Reusable USB NCM transport helpers for A90 revalidation runners."""

from __future__ import annotations

import datetime as dt
import hashlib
import http.server
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import tarfile
import threading
import time
from pathlib import Path
from typing import Any, Callable


A90_USB_VENDOR_ID = "04e8"
A90_USB_PRODUCT_ID = "6861"
A90_USB_NCM_DRIVER = "cdc_ncm"
DEFAULT_DEVICE_IFNAME = "ncm0"
DEFAULT_DEVICE_IP = "192.168.7.2"
DEFAULT_DEVICE_NETMASK = "255.255.255.0"
DEFAULT_NM_PROFILE = "a90-v725-ncm-bench"

RunStep = Callable[..., dict[str, Any]]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_command(command: list[object], *, timeout: float) -> dict[str, Any]:
    started = now_iso()
    try:
        completed = subprocess.run(
            [str(item) for item in command],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "command": [str(item) for item in command],
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
            "command": [str(item) for item in command],
            "started": started,
            "ended": now_iso(),
            "timeout": True,
            "rc": None,
            "ok": False,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line or line.startswith("["):
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_compact_step(store: Any,
                       steps: list[dict[str, Any]],
                       name: str,
                       *,
                       command: list[object],
                       ok: bool,
                       rc: int,
                       stdout: str = "",
                       stderr: str = "") -> None:
    stdout_file = f"{name}.stdout.txt"
    stderr_file = f"{name}.stderr.txt"
    store.write_text(stdout_file, stdout)
    store.write_text(stderr_file, stderr)
    steps.append({
        "name": name,
        "command": [str(item) for item in command],
        "started": now_iso(),
        "ended": now_iso(),
        "timeout": False,
        "rc": rc,
        "ok": ok,
        "stdout_file": stdout_file,
        "stderr_file": stderr_file,
    })


class FastTransferHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "A90FastTransferHTTP/1"

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        expected_path = "/" + self.server.file_path.name  # type: ignore[attr-defined]
        if self.path.split("?", 1)[0] != expected_path:
            self.send_error(404, "not found")
            return
        data = self.server.file_path.read_bytes()  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(data)
            self.wfile.flush()
            self.server.served_count += 1  # type: ignore[attr-defined]
        except (BrokenPipeError, ConnectionResetError) as exc:
            self.server.request_log.append(f"client-closed-during-body: {exc}")  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        self.server.request_log.append(fmt % args)  # type: ignore[attr-defined]


class IPv6ThreadingHTTPServer(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6
    daemon_threads = True
    allow_reuse_address = True


class SingleFileHttpServer:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.server: IPv6ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port = 0

    def __enter__(self) -> "SingleFileHttpServer":
        server = IPv6ThreadingHTTPServer(("::", 0), FastTransferHandler)
        server.file_path = self.file_path  # type: ignore[attr-defined]
        server.request_log = []  # type: ignore[attr-defined]
        server.served_count = 0  # type: ignore[attr-defined]
        self.server = server
        self.port = int(server.server_address[1])
        self.thread = threading.Thread(target=server.serve_forever, name="a90-ncm-transfer-http", daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2.0)

    def manifest(self) -> dict[str, Any]:
        server = self.server
        return {
            "port": self.port,
            "file": self.file_path.name,
            "served_count": int(getattr(server, "served_count", 0)) if server is not None else 0,
            "request_log": list(getattr(server, "request_log", [])) if server is not None else [],
        }


class TcpArchiveReceiver:
    def __init__(self, archive_path: Path, *, timeout: float = 45.0) -> None:
        self.archive_path = archive_path
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.thread: threading.Thread | None = None
        self.port = 0
        self.result: dict[str, Any] = {
            "ok": False,
            "bytes": 0,
            "sha256": "",
            "elapsed_sec": 0.0,
            "error": "",
        }

    def __enter__(self) -> "TcpArchiveReceiver":
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("::", 0))
        sock.listen(1)
        sock.settimeout(self.timeout)
        self.sock = sock
        self.port = int(sock.getsockname()[1])
        self.thread = threading.Thread(target=self._receive, name="a90-ncm-archive-receiver", daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.sock is not None:
            self.sock.close()
        if self.thread is not None:
            self.thread.join(timeout=max(1.0, self.timeout))

    def _receive(self) -> None:
        started = time.monotonic()
        try:
            assert self.sock is not None
            conn, _addr = self.sock.accept()
            total = 0
            digest = hashlib.sha256()
            self.archive_path.parent.mkdir(parents=True, exist_ok=True)
            with conn, self.archive_path.open("wb") as handle:
                conn.settimeout(self.timeout)
                while True:
                    chunk = conn.recv(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    total += len(chunk)
            self.result.update({
                "ok": total > 0,
                "bytes": total,
                "sha256": digest.hexdigest() if total > 0 else "",
                "elapsed_sec": round(time.monotonic() - started, 3),
                "error": "" if total > 0 else "empty-stream",
            })
        except Exception as exc:  # noqa: BLE001 - transport evidence should preserve exact failure
            self.result.update({
                "ok": False,
                "elapsed_sec": round(time.monotonic() - started, 3),
                "error": repr(exc),
            })


class TcpProbeReceiver:
    def __init__(self, *, timeout: float = 8.0) -> None:
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.thread: threading.Thread | None = None
        self.port = 0
        self.payload = b""
        self.error = ""

    def __enter__(self) -> "TcpProbeReceiver":
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("::", 0))
        sock.listen(1)
        sock.settimeout(self.timeout)
        self.sock = sock
        self.port = int(sock.getsockname()[1])
        self.thread = threading.Thread(target=self._receive, name="a90-ncm-transfer-probe", daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.sock is not None:
            self.sock.close()
        if self.thread is not None:
            self.thread.join(timeout=1.0)

    def _receive(self) -> None:
        try:
            assert self.sock is not None
            conn, _addr = self.sock.accept()
            with conn:
                conn.settimeout(self.timeout)
                self.payload = conn.recv(128)
        except Exception as exc:  # noqa: BLE001 - readiness probe should capture exact failure
            self.error = repr(exc)


def netdev_driver_for(ifname: str) -> str:
    driver_path = Path("/sys/class/net") / ifname / "device" / "driver"
    try:
        return driver_path.resolve().name
    except OSError:
        return ""


def usb_attrs_for_netdev(ifname: str) -> dict[str, str]:
    attrs = {
        "idVendor": "",
        "idProduct": "",
        "manufacturer": "",
        "product": "",
        "serial": "",
        "bInterfaceClass": "",
        "bInterfaceSubClass": "",
        "bInterfaceProtocol": "",
        "bInterfaceNumber": "",
        "interface": "",
    }
    try:
        device = (Path("/sys/class/net") / ifname / "device").resolve()
    except OSError:
        return attrs
    for path in (device, *device.parents):
        for key in list(attrs):
            if attrs[key]:
                continue
            attr_path = path / key
            if attr_path.exists():
                attrs[key] = attr_path.read_text(encoding="utf-8", errors="replace").strip()
        if attrs["idVendor"] and attrs["idProduct"] and attrs["bInterfaceClass"]:
            break
    return attrs


def udev_properties_for_netdev(ifname: str) -> dict[str, str]:
    if shutil.which("udevadm") is None:
        return {}
    result = run_command(
        ["udevadm", "info", "-q", "property", "-p", f"/sys/class/net/{ifname}"],
        timeout=5,
    )
    if not result.get("ok"):
        return {}
    properties: dict[str, str] = {}
    for raw_line in str(result.get("stdout") or "").splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        properties[key] = value
    return properties


def cdc_ncm_sysfs_snapshot(ifname: str) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    base = Path("/sys/class/net") / ifname / "cdc_ncm"
    if not base.is_dir():
        return snapshot
    for path in sorted(base.iterdir()):
        if not path.is_file():
            continue
        try:
            snapshot[path.name] = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError as exc:
            snapshot[path.name] = f"<read-error:{exc.errno}>"
    return snapshot


def is_a90_ncm_netdev(item: dict[str, Any]) -> bool:
    return (
        str(item.get("driver") or "") == A90_USB_NCM_DRIVER
        and str(item.get("usb_vendor") or "").lower() == A90_USB_VENDOR_ID
    )


def host_netdev_snapshot() -> list[dict[str, Any]]:
    result = run_command(["ip", "-j", "addr", "show"], timeout=10)
    if not result.get("ok"):
        return []
    try:
        entries = json.loads(str(result.get("stdout") or "[]"))
    except json.JSONDecodeError:
        return []
    snapshot: list[dict[str, Any]] = []
    for entry in entries:
        ifname = str(entry.get("ifname") or "")
        addrs = entry.get("addr_info") if isinstance(entry.get("addr_info"), list) else []
        link_local = ""
        ipv4_addrs: list[str] = []
        for addr in addrs:
            if not isinstance(addr, dict):
                continue
            local = str(addr.get("local") or "")
            if addr.get("family") == "inet":
                ipv4_addrs.append(local)
            elif addr.get("family") == "inet6" and local.startswith("fe80:") and not link_local:
                link_local = local
        sysfs_path = ""
        try:
            sysfs_path = str((Path("/sys/class/net") / ifname).resolve())
        except OSError:
            sysfs_path = ""
        driver = netdev_driver_for(ifname)
        usb_attrs = usb_attrs_for_netdev(ifname)
        udev_props = udev_properties_for_netdev(ifname)
        if not driver:
            driver = udev_props.get("ID_NET_DRIVER", "")
        usb_vendor = (
            usb_attrs.get("idVendor")
            or udev_props.get("ID_USB_VENDOR_ID")
            or udev_props.get("ID_VENDOR_ID")
            or ""
        ).lower()
        usb_product = (
            usb_attrs.get("idProduct")
            or udev_props.get("ID_USB_MODEL_ID")
            or udev_props.get("ID_MODEL_ID")
            or ""
        ).lower()
        usb_manufacturer = usb_attrs.get("manufacturer") or udev_props.get("ID_USB_VENDOR") or ""
        usb_product_name = usb_attrs.get("product") or udev_props.get("ID_USB_MODEL") or ""
        usb_serial = usb_attrs.get("serial") or udev_props.get("ID_USB_SERIAL_SHORT") or ""
        interface_class = usb_attrs.get("bInterfaceClass") or ""
        interface_subclass = usb_attrs.get("bInterfaceSubClass") or ""
        interface_protocol = usb_attrs.get("bInterfaceProtocol") or ""
        interface_number = usb_attrs.get("bInterfaceNumber") or udev_props.get("ID_USB_INTERFACE_NUM") or ""
        a90_ncm = driver == A90_USB_NCM_DRIVER and usb_vendor == A90_USB_VENDOR_ID
        snapshot.append({
            "ifname": ifname,
            "operstate": str(entry.get("operstate") or ""),
            "address": str(entry.get("address") or ""),
            "driver": driver,
            "usb_vendor": usb_vendor,
            "usb_product": usb_product,
            "usb_manufacturer": usb_manufacturer,
            "usb_product_name": usb_product_name,
            "usb_serial": usb_serial,
            "interface_class": interface_class,
            "interface_subclass": interface_subclass,
            "interface_protocol": interface_protocol,
            "interface_number": interface_number,
            "link_local": link_local,
            "ipv4": ipv4_addrs,
            "sysfs_path": sysfs_path,
            "udev": {
                key: udev_props.get(key, "")
                for key in (
                    "ID_NET_DRIVER",
                    "ID_USB_VENDOR_ID",
                    "ID_USB_MODEL_ID",
                    "ID_USB_INTERFACE_NUM",
                    "ID_USB_SERIAL_SHORT",
                    "ID_USB_INTERFACES",
                    "ID_MM_CANDIDATE",
                )
            },
            "cdc_ncm": cdc_ncm_sysfs_snapshot(ifname),
            "a90_ncm": a90_ncm,
            "likely_usb_ncm": a90_ncm,
        })
    return snapshot


def host_ncm_candidates(snapshot: list[dict[str, Any]], *, require_link_local: bool) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in snapshot:
        if not item.get("likely_usb_ncm"):
            continue
        if require_link_local and not str(item.get("link_local") or "").startswith("fe80:"):
            continue
        candidates.append(item)
    candidates.sort(key=lambda item: (
        0 if item.get("usb_product") == A90_USB_PRODUCT_ID else 1,
        0 if str(item.get("link_local") or "").startswith("fe80:") else 1,
        0 if item.get("interface_number") == "02" else 1,
        str(item.get("ifname") or ""),
    ))
    return candidates


def safe_host_ifname(ifname: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.:-]+", ifname)) and "/" not in ifname and ifname not in {".", ".."}


class FastTransferSession:
    def __init__(self,
                 store: Any,
                 steps: list[dict[str, Any]],
                 *,
                 run_step: RunStep,
                 enabled: bool = True,
                 device_ifname: str = DEFAULT_DEVICE_IFNAME,
                 device_ip: str = DEFAULT_DEVICE_IP,
                 device_netmask: str = DEFAULT_DEVICE_NETMASK,
                 nm_profile: str = DEFAULT_NM_PROFILE) -> None:
        self.store = store
        self.steps = steps
        self.run_step = run_step
        self.enabled = enabled
        self.device_ifname = device_ifname
        self.device_ip = device_ip
        self.device_netmask = device_netmask
        self.nm_profile = nm_profile
        self.attempted = False
        self.ready = False
        self.closed = False
        self.ifname = ""
        self.host_link_local = ""
        self.reason = "not-started"
        self.device_probe_ok = False
        self.nm_repair_attempted = False

    def select_ready_candidate(self, snapshot: list[dict[str, Any]], *, reason: str) -> bool:
        candidates = host_ncm_candidates(snapshot, require_link_local=True)
        if not candidates:
            return False
        item = candidates[0]
        self.ifname = str(item.get("ifname") or "")
        self.host_link_local = str(item.get("link_local") or "")
        self.ready = bool(self.ifname and self.host_link_local)
        if self.ready:
            self.reason = reason
        return self.ready

    def repair_host_linklocal(self, *, reason: str) -> bool:
        if self.nm_repair_attempted:
            self.reason = "host-ncm-nm-repair-already-attempted"
            return False
        self.nm_repair_attempted = True
        snapshot = host_netdev_snapshot()
        candidates = host_ncm_candidates(snapshot, require_link_local=False)
        if not candidates:
            self.reason = "host-a90-ncm-interface-not-found-for-nm-repair"
            write_compact_step(
                self.store,
                self.steps,
                "fast-transfer-host-nm-linklocal-repair-skipped",
                command=["host", "nmcli", "a90-linklocal-repair"],
                ok=False,
                rc=1,
                stdout=json.dumps({"reason": self.reason, "snapshot": snapshot}, ensure_ascii=False, sort_keys=True) + "\n",
            )
            return False
        ifname = str(candidates[0].get("ifname") or "")
        if not safe_host_ifname(ifname):
            self.reason = "unsafe-host-ncm-ifname"
            write_compact_step(
                self.store,
                self.steps,
                "fast-transfer-host-nm-linklocal-repair-skipped",
                command=["host", "nmcli", "a90-linklocal-repair"],
                ok=False,
                rc=1,
                stdout=json.dumps({"reason": self.reason, "ifname": ifname}, ensure_ascii=False, sort_keys=True) + "\n",
            )
            return False
        if shutil.which("nmcli") is None:
            self.reason = "nmcli-not-found"
            write_compact_step(
                self.store,
                self.steps,
                "fast-transfer-host-nm-linklocal-repair-skipped",
                command=["host", "nmcli", "a90-linklocal-repair"],
                ok=False,
                rc=1,
                stdout=json.dumps({"reason": self.reason, "ifname": ifname}, ensure_ascii=False, sort_keys=True) + "\n",
            )
            return False

        commands = [
            ["nmcli", "con", "delete", self.nm_profile],
            [
                "nmcli",
                "con",
                "add",
                "type",
                "ethernet",
                "ifname",
                ifname,
                "con-name",
                self.nm_profile,
                "ipv4.method",
                "disabled",
                "ipv6.method",
                "link-local",
                "connection.autoconnect",
                "no",
            ],
            ["nmcli", "con", "up", self.nm_profile],
        ]
        command_results: list[dict[str, Any]] = []
        repair_ok = True
        for index, command in enumerate(commands):
            result = run_command(command, timeout=20)
            command_results.append({
                "command": command,
                "rc": result.get("rc"),
                "ok": result.get("ok"),
                "stdout": str(result.get("stdout") or "")[-1000:],
                "stderr": str(result.get("stderr") or "")[-1000:],
            })
            if index == 0:
                continue
            repair_ok = repair_ok and bool(result.get("ok"))
        time.sleep(1.5)
        after = host_netdev_snapshot()
        ready_after = self.select_ready_candidate(after, reason="nm-linklocal-repair")
        if not ready_after:
            self.reason = "nm-linklocal-repair-did-not-produce-host-fe80"
        write_compact_step(
            self.store,
            self.steps,
            "fast-transfer-host-nm-linklocal-repair",
            command=["host", "nmcli", "a90-linklocal-repair", ifname],
            ok=repair_ok and ready_after,
            rc=0 if repair_ok and ready_after else 1,
            stdout=json.dumps({
                "ok": repair_ok and ready_after,
                "reason": "ok" if repair_ok and ready_after else self.reason,
                "trigger_reason": reason,
                "profile": self.nm_profile,
                "ifname": ifname,
                "commands": command_results,
                "before": snapshot,
                "after": after,
                "host_link_local": self.host_link_local,
            }, ensure_ascii=False, sort_keys=True) + "\n",
        )
        return repair_ok and ready_after

    def ensure_ready(self) -> bool:
        if not self.enabled:
            self.reason = "disabled"
            return False
        if self.ready:
            return True
        if self.attempted:
            return False
        before = host_netdev_snapshot()
        write_compact_step(
            self.store,
            self.steps,
            "fast-transfer-host-net-before",
            command=["host", "ip", "-j", "addr", "show"],
            ok=True,
            rc=0,
            stdout=json.dumps(before, ensure_ascii=False, sort_keys=True) + "\n",
        )
        if self.select_ready_candidate(before, reason="existing-a90-ncm-link-local"):
            write_compact_step(
                self.store,
                self.steps,
                "fast-transfer-host-net-existing",
                command=["host", "detect-existing-a90-ncm-link-local"],
                ok=True,
                rc=0,
                stdout=json.dumps({
                    "ifname": self.ifname,
                    "host_link_local": self.host_link_local,
                    "snapshot": before,
                }, ensure_ascii=False, sort_keys=True) + "\n",
            )
            return True
        if host_ncm_candidates(before, require_link_local=False):
            if self.repair_host_linklocal(reason="a90-ncm-present-without-host-fe80"):
                return True
        self.attempted = True
        self.run_step(
            self.store,
            self.steps,
            "fast-transfer-ncm-start",
            ["run", "/cache/bin/a90_usbnet", "ncm"],
            timeout=8,
            bridge_timeout=3,
        )
        time.sleep(4.0)
        up_script = (
            f"/cache/bin/busybox ifconfig {self.device_ifname} "
            f"{self.device_ip} netmask {self.device_netmask} up 2>&1; "
            f"echo fast_transfer.ifconfig_rc=$?; "
            f"/cache/bin/busybox ip addr show {self.device_ifname} 2>&1"
        )
        self.run_step(
            self.store,
            self.steps,
            "fast-transfer-device-ncm-up",
            ["run", "/cache/bin/busybox", "sh", "-c", up_script],
            timeout=12,
            bridge_timeout=5,
        )
        deadline = time.monotonic() + 15.0
        snapshot: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            snapshot = host_netdev_snapshot()
            if self.select_ready_candidate(snapshot, reason="ok"):
                write_compact_step(
                    self.store,
                    self.steps,
                    "fast-transfer-host-net-ready",
                    command=["host", "detect-a90-ncm-link-local"],
                    ok=True,
                    rc=0,
                    stdout=json.dumps({
                        "ifname": self.ifname,
                        "host_link_local": self.host_link_local,
                        "snapshot": snapshot,
                    }, ensure_ascii=False, sort_keys=True) + "\n",
                )
                return True
            if host_ncm_candidates(snapshot, require_link_local=False):
                if self.repair_host_linklocal(reason="a90-ncm-after-usbnet-without-host-fe80"):
                    return True
            time.sleep(0.5)
        self.reason = "host-a90-ncm-link-local-not-found"
        write_compact_step(
            self.store,
            self.steps,
            "fast-transfer-host-net-ready",
            command=["host", "detect-a90-ncm-link-local"],
            ok=False,
            rc=1,
            stdout=json.dumps({"reason": self.reason, "snapshot": snapshot}, ensure_ascii=False, sort_keys=True) + "\n",
        )
        return False

    def probe_device_to_host(self, *, label: str) -> bool:
        with TcpProbeReceiver(timeout=8.0) as probe:
            script = (
                f"printf a90-fast-probe | /cache/bin/busybox nc -w 3 "
                f"{shlex.quote(self.host_link_local + '%' + self.device_ifname)} {probe.port}; "
                "echo fast_transfer.device_probe_rc=$?"
            )
            step = self.run_step(
                self.store,
                self.steps,
                f"fast-transfer-device-host-probe{label}",
                ["run", "/cache/bin/busybox", "sh", "-c", script],
                timeout=20,
                bridge_timeout=10,
            )
        output = "\n".join([str(step.get("stdout") or ""), str(step.get("stderr") or "")])
        fields = parse_key_values(output)
        probe_ok = (
            probe.payload == b"a90-fast-probe"
            and (bool(step.get("ok")) or fields.get("fast_transfer.device_probe_rc") in {"", "0"})
        )
        if not probe_ok:
            self.reason = f"device-to-host-ncm-probe-failed{label}"
        write_compact_step(
            self.store,
            self.steps,
            f"fast-transfer-device-host-probe-result{label}",
            command=["fast-transfer-device-probe-result"],
            ok=probe_ok,
            rc=0 if probe_ok else 1,
            stdout=json.dumps({
                "ok": probe_ok,
                "reason": "ok" if probe_ok else self.reason,
                "payload": probe.payload.decode("ascii", errors="replace"),
                "receiver_error": probe.error,
                "host_ifname": self.ifname,
                "host_link_local": self.host_link_local,
                "device_ifname": self.device_ifname,
            }, ensure_ascii=False, sort_keys=True) + "\n",
        )
        return probe_ok

    def ensure_device_reachable(self) -> bool:
        if self.device_probe_ok:
            return True
        if not self.ensure_ready():
            return False
        self.device_probe_ok = self.probe_device_to_host(label="")
        if self.device_probe_ok:
            return True
        if self.repair_host_linklocal(reason=self.reason):
            self.device_probe_ok = self.probe_device_to_host(label="-after-nm-repair")
        return self.device_probe_ok

    def transfer_file(self,
                      *,
                      label: str,
                      local_path: Path,
                      remote_path: str,
                      expected_sha256: str,
                      mode: str = "600") -> dict[str, Any]:
        started = time.monotonic()
        if not self.ensure_device_reachable():
            result = {
                "ok": False,
                "reason": self.reason,
                "method": "ncm-wget",
                "elapsed_sec": 0.0,
            }
            write_compact_step(
                self.store,
                self.steps,
                f"{label}-fast-wget-skipped",
                command=["fast-transfer", str(local_path), remote_path],
                ok=False,
                rc=1,
                stdout=json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n",
            )
            return result
        tmp_remote = f"{remote_path}.tmp.{os.getpid()}"
        with SingleFileHttpServer(local_path) as httpd:
            url = f"http://[{self.host_link_local}%{self.device_ifname}]:{httpd.port}/{local_path.name}"
            wait_ipv6 = (
                "i=0; "
                "while [ \"$i\" -lt 8 ]; do "
                f"ll=$(/cache/bin/busybox ip -6 addr show {self.device_ifname} 2>/dev/null); "
                "echo \"$ll\" | /cache/bin/busybox grep -q 'inet6 fe80:' && "
                "! echo \"$ll\" | /cache/bin/busybox grep -q tentative && break; "
                "i=$((i+1)); /cache/bin/busybox sleep 1; "
                "done; echo fast_transfer.ipv6_wait=$i; "
            )
            script = (
                wait_ipv6 +
                f"/cache/bin/busybox rm -f {shlex.quote(tmp_remote)} {shlex.quote(remote_path)}; "
                f"/cache/bin/busybox wget -O {shlex.quote(tmp_remote)} {shlex.quote(url)}; "
                f"rc=$?; echo fast_transfer.wget_rc=$rc; "
                f"if [ \"$rc\" -eq 0 ]; then "
                f"/cache/bin/busybox chmod {shlex.quote(mode)} {shlex.quote(tmp_remote)}; "
                f"/cache/bin/busybox mv -f {shlex.quote(tmp_remote)} {shlex.quote(remote_path)}; "
                f"printf 'fast_transfer.remote_sha256='; /cache/bin/busybox sha256sum {shlex.quote(remote_path)} | /cache/bin/busybox awk '{{print $1}}'; "
                f"printf 'fast_transfer.remote_size='; /cache/bin/busybox stat -c '%s' {shlex.quote(remote_path)} 2>/dev/null; "
                f"fi; exit \"$rc\""
            )
            step = self.run_step(
                self.store,
                self.steps,
                f"{label}-fast-wget",
                ["run", "/cache/bin/busybox", "sh", "-c", script],
                timeout=35,
                bridge_timeout=10,
            )
            output = "\n".join([str(step.get("stdout") or ""), str(step.get("stderr") or "")])
            fields = parse_key_values(output)
            remote_sha = fields.get("fast_transfer.remote_sha256", "")
            if not remote_sha and expected_sha256 in output:
                remote_sha = expected_sha256
            if remote_sha != expected_sha256:
                verify_script = (
                    f"printf 'fast_transfer.remote_sha256='; "
                    f"/cache/bin/busybox sha256sum {shlex.quote(remote_path)} 2>/dev/null | "
                    f"/cache/bin/busybox awk '{{print $1}}'; "
                    f"printf 'fast_transfer.remote_size='; "
                    f"/cache/bin/busybox stat -c '%s' {shlex.quote(remote_path)} 2>/dev/null"
                )
                verify_step = self.run_step(
                    self.store,
                    self.steps,
                    f"{label}-fast-verify",
                    ["run", "/cache/bin/busybox", "sh", "-c", verify_script],
                    timeout=30,
                    bridge_timeout=20,
                )
                verify_output = "\n".join([
                    str(verify_step.get("stdout") or ""),
                    str(verify_step.get("stderr") or ""),
                ])
                verify_fields = parse_key_values(verify_output)
                fields.update({key: value for key, value in verify_fields.items() if value})
                remote_sha = fields.get("fast_transfer.remote_sha256", "")
                if not remote_sha and expected_sha256 in verify_output:
                    remote_sha = expected_sha256
            ok = remote_sha == expected_sha256
            result = {
                "ok": ok,
                "reason": "ok" if ok else "wget-or-sha-failed",
                "method": "ncm-wget",
                "remote_sha256": remote_sha,
                "remote_size": fields.get("fast_transfer.remote_size", ""),
                "wget_rc": fields.get("fast_transfer.wget_rc", ""),
                "http": httpd.manifest(),
                "host_ifname": self.ifname,
                "host_link_local": self.host_link_local,
                "elapsed_sec": round(time.monotonic() - started, 3),
            }
        write_compact_step(
            self.store,
            self.steps,
            f"{label}-fast-wget-result",
            command=["fast-transfer-result", str(local_path), remote_path],
            ok=ok,
            rc=0 if ok else 1,
            stdout=json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n",
        )
        return result

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        if not self.attempted:
            return
        self.run_step(
            self.store,
            self.steps,
            "fast-transfer-ncm-off",
            ["run", "/cache/bin/a90_usbnet", "off"],
            timeout=8,
            bridge_timeout=3,
        )
        time.sleep(4.0)
        self.run_step(
            self.store,
            self.steps,
            "fast-transfer-post-off-netservice-status",
            ["netservice", "status"],
            timeout=30,
            bridge_timeout=20,
        )


def scan_secret_bytes(data: bytes, secret_patterns: dict[str, bytes]) -> list[str]:
    hits: list[str] = []
    for key, pattern in secret_patterns.items():
        if pattern and pattern in data:
            hits.append(key)
    return hits


def validate_uploaded_archive(archive_path: Path,
                              *,
                              secret_patterns: dict[str, bytes] | None = None,
                              forbidden_patterns: tuple[str, ...] = (
                                  "connect_config",
                                  "connect-config",
                                  "sockets",
                                  ".b64",
                                  "wpa_supplicant.conf",
                                  "env",
                              )) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "exists": archive_path.exists(),
        "bytes": archive_path.stat().st_size if archive_path.exists() else 0,
        "sha256": sha256_file(archive_path) if archive_path.exists() else "",
        "entries": [],
        "forbidden_entries": [],
        "secret_hits": [],
        "archive_deleted": False,
        "connect_result_text": "",
        "reason": "archive-missing",
    }
    if not archive_path.exists() or result["bytes"] <= 0:
        return result

    patterns = secret_patterns or {}
    secret_hits = set(scan_secret_bytes(archive_path.read_bytes(), patterns))
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            entries = tar.getmembers()
            names = [member.name for member in entries]
            result["entries"] = names
            result["forbidden_entries"] = [
                name
                for name in names
                if any(pattern in name.lower() for pattern in forbidden_patterns)
            ]
            for member in entries:
                if not member.isfile():
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                data = extracted.read()
                secret_hits.update(scan_secret_bytes(data, patterns))
                if member.name.endswith("/connect-result.txt") or member.name == "connect-result.txt":
                    result["connect_result_text"] = data.decode("utf-8", errors="replace")
    except tarfile.TarError as exc:
        result["reason"] = f"tar-validate-failed:{exc}"
        return result

    result["secret_hits"] = sorted(secret_hits)
    if result["secret_hits"]:
        archive_path.unlink(missing_ok=True)
        result["archive_deleted"] = True
        result["ok"] = False
        result["reason"] = "secret-hit"
        return result
    if result["forbidden_entries"]:
        result["ok"] = False
        result["reason"] = "forbidden-entry"
        return result
    if not result["entries"]:
        result["ok"] = False
        result["reason"] = "empty-tar"
        return result
    result["ok"] = True
    result["reason"] = "ok"
    return result
