#!/usr/bin/env python3
"""Host-local A90B1 command broker for A90 native-init control paths."""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import queue
import re
import shlex
import socket
import stat
import struct
import sys
import tempfile
import threading
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90ctl import ProtocolResult, run_cmdv1_command
from a90harness.evidence import append_private_jsonl, ensure_private_dir, write_private_json, write_private_text


PROTO = "A90B1"
DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 54321
DEFAULT_DEVICE_IP = "192.168.7.2"
DEFAULT_TCP_PORT = 2325
DEFAULT_TCP_TIMEOUT = 10.0
DEFAULT_TOKEN_COMMAND = ("netservice", "token", "show")
DEFAULT_TOKEN_PATH = "/cache/native-init-tcpctl.token"
SENSITIVE_DEVICE_READ_PATHS = {
    DEFAULT_TOKEN_PATH,
}
SENSITIVE_DEVICE_READ_PREFIXES = (
    "/mnt/sdext/a90/runtime/",
    "/cache/a90/runtime/",
)
DEFAULT_RUNTIME_DIR = Path("tmp/a90-broker")
DEFAULT_SOCKET_NAME = "a90b1.sock"
DEFAULT_AUDIT_NAME = "audit.jsonl"
MAX_REQUEST_BYTES = 64 * 1024
MAX_TIMEOUT_MS = 5 * 60 * 1000
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,96}$")
CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_.:@%+=,-]{1,128}$")
TOKEN_RE = re.compile(r"^[0-9A-Fa-f]{24,}$")
TOKEN_TEXT_RE = re.compile(r"(tcpctl_token=)[0-9A-Fa-f]{24,}|(?<![0-9A-Fa-f])[0-9A-Fa-f]{32,}(?![0-9A-Fa-f])")
SENSITIVE_ARG_WORDS = {
    "auth",
    "credential",
    "key",
    "passwd",
    "password",
    "secret",
    "token",
}


OBSERVE_COMMANDS = {
    "version",
    "status",
    "bootstatus",
    "selftest",
    "pid1guard",
    "runtime",
    "storage",
    "mountsd",
    "helpers",
    "userland",
    "service",
    "netservice",
    "rshell",
    "diag",
    "wififeas",
    "wifiinv",
    "logpath",
    "hudlog",
    "timeline",
    "last",
    "pwd",
    "uname",
    "mounts",
    "ls",
    "stat",
    "exposure",
    "policycheck",
    "kernelinv",
    "sensormap",
    "pstore",
    "watchdoginv",
    "tracefs",
}

OPERATOR_COMMANDS = {
    "screenmenu",
    "menu",
    "hide",
    "hidemenu",
    "resume",
    "autohud",
    "stophud",
    "longsoak",
    "statushud",
    "watchhud",
    "cat",
}

EXCLUSIVE_COMMANDS = {
    "run",
    "runandroid",
    "cpustress",
    "mountsystem",
    "prepareandroid",
    "startadbd",
    "stopadbd",
    "netservice",
    "rshell",
    "usbacmreset",
    "helper",
    "helpers",
    "userland",
}

REBINDS_OR_DESTRUCTIVE_COMMANDS = {
    "reboot",
    "recovery",
    "poweroff",
}

OBSERVE_SUBCOMMANDS = {
    "mountsd": {"status"},
    "netservice": {"status"},
    "rshell": {"status", "audit"},
    "service": {"list", "status"},
    "helpers": {"status", "list", "verify"},
    "userland": {"status", "verbose"},
    "hudlog": {"status"},
    "longsoak": {"status"},
}

ABSENT_SUBCOMMAND_DEFAULTS_TO_STATUS = {
    "netservice",
    "rshell",
    "service",
    "helpers",
    "userland",
    "hudlog",
}


@dataclass(frozen=True)
class BrokerRequest:
    request_id: str
    client_id: str
    op: str
    argv: list[str]
    timeout_ms: int
    command_class: str


@dataclass
class BrokerResponse:
    proto: str
    request_id: str
    ok: bool
    rc: int | None
    status: str
    duration_ms: int
    backend: str
    command_class: str
    text: str
    error: str = ""

    def to_wire(self) -> dict[str, Any]:
        return {
            "proto": self.proto,
            "id": self.request_id,
            "ok": self.ok,
            "rc": self.rc,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "backend": self.backend,
            "class": self.command_class,
            "text": self.text,
            "error": self.error,
        }


@dataclass(frozen=True)
class WorkItem:
    request: BrokerRequest
    response_queue: "queue.Queue[BrokerResponse]"


@dataclass(frozen=True)
class BrokerPolicy:
    allow_operator: bool = False
    allow_exclusive: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "allow_operator": self.allow_operator,
            "allow_exclusive": self.allow_exclusive,
            "allow_rebind_destructive": False,
        }

    def authorize(self, request: BrokerRequest) -> None:
        deny_sensitive_read(request)
        if request.command_class == "observe":
            return
        if request.command_class == "operator-action":
            if self.allow_operator or self.allow_exclusive:
                return
            raise BrokerError(
                "operator-required",
                "operator-action command requires --allow-operator or --allow-exclusive",
            )
        if request.command_class == "exclusive":
            if self.allow_exclusive:
                return
            raise BrokerError(
                "exclusive-required",
                "exclusive command requires --allow-exclusive",
            )
        if request.command_class == "rebind-destructive":
            raise BrokerError(
                "operator-required",
                "rebind/destructive command is not broker-multiplexed; use foreground raw control",
            )
        raise BrokerError("bad-request", f"unsupported command class: {request.command_class}")


class BrokerError(RuntimeError):
    def __init__(self, status: str, message: str) -> None:
        super().__init__(message)
        self.status = status


def normalize_device_path(path: str) -> str:
    if path.startswith("/"):
        return posixpath.normpath(path)
    return posixpath.normpath("/" + path)


def is_sensitive_device_read_path(path: str) -> bool:
    normalized = normalize_device_path(path)
    if normalized in SENSITIVE_DEVICE_READ_PATHS:
        return True
    return any(
        normalized == prefix.rstrip("/") or normalized.startswith(prefix)
        for prefix in SENSITIVE_DEVICE_READ_PREFIXES
    )


def deny_sensitive_read(request: BrokerRequest) -> None:
    if request.argv and request.argv[0] == "cat" and len(request.argv) > 1:
        if is_sensitive_device_read_path(request.argv[1]):
            raise BrokerError(
                "sensitive-path-denied",
                "cat of sensitive device path is blocked by broker policy",
            )


class Backend:
    name = "backend"

    def execute(self, request: BrokerRequest) -> "BackendResult":
        raise NotImplementedError

    def metadata(self) -> dict[str, Any]:
        return {"backend": self.name}


@dataclass(frozen=True)
class BackendResult:
    rc: int
    status: str
    text: str
    backend: str


class AcmCmdv1Backend(Backend):
    name = "acm-cmdv1"

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

    def execute(self, request: BrokerRequest) -> BackendResult:
        result: ProtocolResult = run_cmdv1_command(
            self.host,
            self.port,
            request.timeout_ms / 1000.0,
            request.argv,
            retry_unsafe=False,
        )
        return BackendResult(result.rc, result.status, result.text, self.name)

    def metadata(self) -> dict[str, Any]:
        return {
            "backend": self.name,
            "bridge_host": self.host,
            "bridge_port": self.port,
        }


class NcmTcpctlBackend(Backend):
    name = "ncm-tcpctl"

    def __init__(self,
                 host: str,
                 port: int,
                 device_ip: str,
                 tcp_port: int,
                 tcp_timeout: float,
                 token: str | None,
                 token_path: str,
                 no_auth: bool) -> None:
        self.acm = AcmCmdv1Backend(host, port)
        self.device_ip = device_ip
        self.tcp_port = tcp_port
        self.tcp_timeout = tcp_timeout
        self.token_path = token_path
        self.token_lock = threading.Lock()
        self.token = token
        self.no_auth = no_auth
        if token is not None:
            self.validate_token(token)

    def execute(self, request: BrokerRequest) -> BackendResult:
        command = self.tcpctl_command(request.argv)
        if command is None:
            return self.acm.execute(request)
        text = self.tcpctl_request(command, request.timeout_ms / 1000.0)
        status = self.tcpctl_status(text)
        return BackendResult(0 if status == "ok" else 1, status, text, self.name)

    def metadata(self) -> dict[str, Any]:
        return {
            "backend": self.name,
            "device_ip": self.device_ip,
            "tcp_port": self.tcp_port,
            "tcp_timeout": self.tcp_timeout,
            "auth": {
                "required": not self.no_auth,
                "token_source": "disabled" if self.no_auth else ("cli" if self.token else "acm-command"),
                "token_path": None if self.no_auth else self.token_path,
            },
            "fallback": self.acm.metadata(),
        }

    @staticmethod
    def tcpctl_command(argv: list[str]) -> str | None:
        if len(argv) >= 2 and argv[0] == "run" and argv[1].startswith("/"):
            return "run " + " ".join(shlex.quote(part) for part in argv[1:])
        return None

    @staticmethod
    def validate_token(token: str) -> str:
        if not TOKEN_RE.match(token):
            raise ValueError("tcpctl token must be a 24+ char hex string")
        return token

    @staticmethod
    def tcpctl_status(text: str) -> str:
        if ("ERR auth-required" in text or
                "ERR auth-failed" in text or
                "ERR auth-token-unavailable" in text):
            return "auth-failed"
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return "error"
        final = lines[-1]
        if final == "OK":
            return "ok"
        if final.startswith("ERR "):
            return "error"
        return "error"

    def tcpctl_request(self, command: str, timeout_sec: float) -> str:
        payload = command.rstrip("\n") + "\n"
        if not self.no_auth and self.command_requires_auth(command):
            payload = f"auth {self.get_token(timeout_sec)}\n{payload}"
        with socket.create_connection((self.device_ip, self.tcp_port), timeout=min(timeout_sec, self.tcp_timeout)) as sock:
            sock.settimeout(0.5)
            sock.sendall(payload.encode())
            data = bytearray()
            deadline = time.monotonic() + min(timeout_sec, self.tcp_timeout)
            while time.monotonic() < deadline:
                try:
                    chunk = sock.recv(8192)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                data.extend(chunk)
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def command_requires_auth(command: str) -> bool:
        word = command.lstrip().split(maxsplit=1)[0] if command.strip() else ""
        return word in {"run", "shutdown"}

    def get_token(self, timeout_sec: float) -> str:
        with self.token_lock:
            if self.token:
                return self.token
            token_request = BrokerRequest(
                request_id="ncm-token",
                client_id="broker",
                op="cmd",
                argv=list(DEFAULT_TOKEN_COMMAND),
                timeout_ms=int(timeout_sec * 1000),
                command_class="observe",
            )
            result = self.acm.execute(token_request)
            if result.rc != 0 or result.status != "ok":
                raise RuntimeError(
                    "token command failed "
                    f"rc={result.rc} status={result.status}\n{redact_text(result.text)}"
                )
            match = re.search(r"tcpctl_token=([0-9A-Fa-f]{32})", result.text)
            if not match:
                raise RuntimeError(f"tcpctl token was not found in output:\n{redact_text(result.text)}")
            self.token = self.validate_token(match.group(1))
            return self.token


class FakeBackend(Backend):
    name = "fake"

    def execute(self, request: BrokerRequest) -> BackendResult:
        if request.argv and request.argv[0] == "fail":
            return BackendResult(1, "error", "fake failure\n", self.name)
        return BackendResult(0, "ok", f"fake {' '.join(request.argv)}\n", self.name)


def log(message: str) -> None:
    print(f"[a90-broker] {message}", file=sys.stderr, flush=True)


def now_ms() -> int:
    return int(time.time() * 1000)


def monotonic_ms() -> int:
    return int(time.monotonic() * 1000)


def command_subcommand(argv: list[str]) -> str | None:
    return argv[1] if len(argv) > 1 else None


def argv_command(argv: list[str]) -> str:
    return argv[0] if argv else ""


def redact_arg(arg: str) -> str:
    lower = arg.lower()
    if TOKEN_RE.match(arg):
        return "<redacted>"
    for word in SENSITIVE_ARG_WORDS:
        if lower == word:
            return arg
        if lower.startswith(word + "=") or lower.startswith("--" + word + "="):
            return arg.split("=", 1)[0] + "=<redacted>"
    return arg


def redact_text(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group(1):
            return match.group(1) + "<redacted>"
        return "<redacted>"

    return TOKEN_TEXT_RE.sub(replace, text)


def redact_argv(argv: list[Any]) -> list[str]:
    redacted: list[str] = []
    hide_next = False
    for item in argv:
        arg = str(item)
        lower = arg.lower().lstrip("-")
        if hide_next:
            redacted.append("<redacted>")
            hide_next = False
            continue
        redacted.append(redact_arg(arg))
        if lower in SENSITIVE_ARG_WORDS and "=" not in arg:
            hide_next = True
    return redacted


def audit_request_payload(request: BrokerRequest) -> dict[str, Any]:
    return {
        "id": request.request_id,
        "client_id": request.client_id,
        "command": argv_command(request.argv),
        "argc": len(request.argv),
        "argv": redact_argv(request.argv),
        "class": request.command_class,
    }


def classify_command(argv: list[str]) -> str:
    if not argv:
        raise BrokerError("bad-request", "argv must not be empty")

    name = argv[0]
    if name in REBINDS_OR_DESTRUCTIVE_COMMANDS:
        return "rebind-destructive"

    allowed_subcommands = OBSERVE_SUBCOMMANDS.get(name)
    if allowed_subcommands is not None:
        subcommand = command_subcommand(argv)
        if subcommand is not None and subcommand in allowed_subcommands:
            return "observe"
        if subcommand is None and name in ABSENT_SUBCOMMAND_DEFAULTS_TO_STATUS:
            return "observe"
        return "exclusive"

    if name in OPERATOR_COMMANDS:
        return "operator-action"
    if name in EXCLUSIVE_COMMANDS:
        return "exclusive"
    if name in OBSERVE_COMMANDS:
        return "observe"
    return "exclusive"


def validate_id(value: Any, label: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str):
        raise BrokerError("bad-request", f"{label} must be a string")
    if not pattern.match(value):
        raise BrokerError("bad-request", f"{label} contains unsupported characters or length")
    return value


def validate_argv(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise BrokerError("bad-request", "argv must be a non-empty list")
    argv: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise BrokerError("bad-request", f"argv[{index}] must be a string")
        if not item or "\x00" in item or "\r" in item or "\n" in item:
            raise BrokerError("bad-request", f"argv[{index}] is empty or contains control separators")
        argv.append(item)
    return argv


def parse_timeout_ms(value: Any) -> int:
    if value is None:
        return 10_000
    if not isinstance(value, int):
        raise BrokerError("bad-request", "timeout_ms must be an integer")
    if value <= 0 or value > MAX_TIMEOUT_MS:
        raise BrokerError("bad-request", f"timeout_ms must be 1..{MAX_TIMEOUT_MS}")
    return value


def parse_wire_request(payload: dict[str, Any]) -> BrokerRequest:
    if payload.get("proto") != PROTO:
        raise BrokerError("bad-request", f"proto must be {PROTO}")
    request_id = validate_id(payload.get("id"), "id", REQUEST_ID_RE)
    client_id = payload.get("client_id", f"pid:{os.getpid()}")
    client_id = validate_id(client_id, "client_id", CLIENT_ID_RE)
    op = payload.get("op")
    if op != "cmd":
        raise BrokerError("bad-request", "only op=cmd is supported")
    argv = validate_argv(payload.get("argv"))
    timeout_ms = parse_timeout_ms(payload.get("timeout_ms"))
    actual_class = classify_command(argv)
    requested_class = payload.get("class")
    if requested_class is not None and requested_class != actual_class:
        raise BrokerError(
            "bad-request",
            f"class mismatch: requested {requested_class!r}, actual {actual_class!r}",
        )
    return BrokerRequest(
        request_id=request_id,
        client_id=client_id,
        op=op,
        argv=argv,
        timeout_ms=timeout_ms,
        command_class=actual_class,
    )


def response_from_error(request_id: str,
                        status: str,
                        message: str,
                        *,
                        command_class: str = "unknown",
                        backend: str = "broker",
                        duration_ms: int = 0) -> BrokerResponse:
    return BrokerResponse(
        proto=PROTO,
        request_id=request_id,
        ok=False,
        rc=None,
        status=status,
        duration_ms=duration_ms,
        backend=backend,
        command_class=command_class,
        text="",
        error=redact_text(message),
    )


def read_json_line(conn: socket.socket) -> dict[str, Any]:
    data = bytearray()
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data.extend(chunk)
        if b"\n" in chunk:
            break
        if len(data) > MAX_REQUEST_BYTES:
            raise BrokerError("bad-request", "request exceeds maximum size")
    line = bytes(data).split(b"\n", 1)[0]
    if not line:
        raise BrokerError("bad-request", "empty request")
    try:
        payload = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BrokerError("bad-request", f"invalid JSON request: {exc}") from exc
    if not isinstance(payload, dict):
        raise BrokerError("bad-request", "request must be a JSON object")
    return payload


def write_json_line(conn: socket.socket, payload: dict[str, Any]) -> None:
    conn.sendall((json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))


def peer_credentials(conn: socket.socket) -> dict[str, int] | None:
    if not hasattr(socket, "SO_PEERCRED"):
        return None
    try:
        data = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        pid, uid, gid = struct.unpack("3i", data)
    except OSError:
        return None
    return {"pid": pid, "uid": uid, "gid": gid}


def safe_unlink_socket(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(info.st_mode):
        raise RuntimeError(f"refusing symlink socket path: {path}")
    if not stat.S_ISSOCK(info.st_mode):
        raise RuntimeError(f"refusing to replace non-socket path: {path}")
    path.unlink()


def prepare_runtime_paths(runtime_dir: Path,
                          socket_name: str,
                          audit_name: str) -> tuple[Path, Path]:
    ensure_private_dir(runtime_dir)
    socket_path = runtime_dir / socket_name
    audit_path = runtime_dir / audit_name
    if socket_path.name != socket_name or "/" in socket_name or socket_name in {"", ".", ".."}:
        raise RuntimeError("socket name must be one path component")
    if audit_path.name != audit_name or "/" in audit_name or audit_name in {"", ".", ".."}:
        raise RuntimeError("audit name must be one path component")
    safe_unlink_socket(socket_path)
    return socket_path, audit_path


class BrokerServer:
    def __init__(self, backend: Backend, socket_path: Path, audit_path: Path, policy: BrokerPolicy | None = None) -> None:
        self.backend = backend
        self.socket_path = socket_path
        self.audit_path = audit_path
        self.policy = policy or BrokerPolicy()
        self.work_queue: "queue.Queue[WorkItem | None]" = queue.Queue()
        self.audit_lock = threading.Lock()
        self.worker = threading.Thread(target=self.worker_loop, name="a90-broker-worker", daemon=True)

    def audit(self, event: str, payload: dict[str, Any]) -> None:
        record = {"ts_ms": now_ms(), "event": event, **payload}
        with self.audit_lock:
            append_private_jsonl(self.audit_path, record)

    def worker_loop(self) -> None:
        while True:
            item = self.work_queue.get()
            if item is None:
                self.work_queue.task_done()
                return
            started = monotonic_ms()
            request = item.request
            self.audit(
                "dispatch",
                {
                    **audit_request_payload(request),
                    "backend": self.backend.name,
                },
            )
            try:
                self.policy.authorize(request)
                result = self.backend.execute(request)
                duration_ms = monotonic_ms() - started
                response = BrokerResponse(
                    proto=PROTO,
                    request_id=request.request_id,
                    ok=result.rc == 0 and result.status == "ok",
                    rc=result.rc,
                    status=result.status,
                    duration_ms=duration_ms,
                    backend=result.backend,
                    command_class=request.command_class,
                    text=result.text,
                )
            except BrokerError as exc:
                duration_ms = monotonic_ms() - started
                response = response_from_error(
                    request.request_id,
                    exc.status,
                    str(exc),
                    command_class=request.command_class,
                    backend=self.backend.name,
                    duration_ms=duration_ms,
                )
            except Exception as exc:  # noqa: BLE001 - broker must report backend failures
                duration_ms = monotonic_ms() - started
                response = response_from_error(
                    request.request_id,
                    "transport-error",
                    f"{type(exc).__name__}: {exc}",
                    command_class=request.command_class,
                    backend=self.backend.name,
                    duration_ms=duration_ms,
                )
            self.audit(
                "result",
                {
                    "id": request.request_id,
                    "client_id": request.client_id,
                    "class": request.command_class,
                    "backend": response.backend,
                    "ok": response.ok,
                    "rc": response.rc,
                    "status": response.status,
                    "duration_ms": response.duration_ms,
                    "error": response.error,
                },
            )
            item.response_queue.put(response)
            self.work_queue.task_done()

    def handle_client(self, conn: socket.socket) -> None:
        request_id = "missing"
        peer = peer_credentials(conn)
        try:
            conn.settimeout(1.0)
            payload = read_json_line(conn)
            request_id = str(payload.get("id", "missing"))
            request = parse_wire_request(payload)
            response_queue: "queue.Queue[BrokerResponse]" = queue.Queue(maxsize=1)
            self.audit(
                "accept",
                {
                    **audit_request_payload(request),
                    "peer": peer,
                },
            )
            self.work_queue.put(WorkItem(request, response_queue))
            response = response_queue.get(timeout=(request.timeout_ms / 1000.0) + 5.0)
        except BrokerError as exc:
            response = response_from_error(request_id, exc.status, str(exc))
        except queue.Empty:
            response = response_from_error(request_id, "timeout", "broker response wait timed out")
        except Exception as exc:  # noqa: BLE001 - keep broker alive after client errors
            response = response_from_error(request_id, "broker-error", f"{type(exc).__name__}: {exc}")
        try:
            write_json_line(conn, response.to_wire())
        finally:
            conn.close()

    def serve_forever(self) -> None:
        self.worker.start()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(self.socket_path))
            os.chmod(self.socket_path, 0o600)
            server.listen(16)
            self.audit(
                "start",
                {"socket": str(self.socket_path), "backend": self.backend.name, "policy": self.policy.to_dict()},
            )
            log(f"ready socket={self.socket_path} backend={self.backend.name}")
            while True:
                conn, _ = server.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn,), daemon=True)
                thread.start()


def connect_and_call(socket_path: Path, payload: dict[str, Any], timeout_sec: float) -> dict[str, Any]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout_sec)
        client.connect(str(socket_path))
        write_json_line(client, payload)
        response = read_json_line(client)
    return response


def build_request(args: argparse.Namespace, argv: list[str]) -> dict[str, Any]:
    request_id = args.request_id or f"req-{uuid.uuid4().hex}"
    payload = {
        "proto": PROTO,
        "id": request_id,
        "client_id": args.client_id,
        "op": "cmd",
        "argv": argv,
        "timeout_ms": int(args.timeout * 1000),
    }
    if args.command_class:
        payload["class"] = args.command_class
    return payload


def make_backend(args: argparse.Namespace) -> Backend:
    if args.backend == "fake":
        return FakeBackend()
    if args.backend == "ncm-tcpctl":
        return NcmTcpctlBackend(
            args.bridge_host,
            args.bridge_port,
            args.device_ip,
            args.tcp_port,
            args.tcp_timeout,
            args.token,
            args.token_path,
            args.no_auth,
        )
    return AcmCmdv1Backend(args.bridge_host, args.bridge_port)


def read_audit_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    malformed: list[dict[str, Any]] = []
    if not path.exists():
        raise RuntimeError(f"audit file does not exist: {path}")
    with path.open("r", encoding="utf-8", errors="replace") as file_obj:
        for line_no, line in enumerate(file_obj, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                malformed.append({"line": line_no, "error": str(exc), "text": text[:200]})
                continue
            if not isinstance(payload, dict):
                malformed.append({"line": line_no, "error": "record is not a JSON object", "text": text[:200]})
                continue
            payload["_line"] = line_no
            records.append(payload)
    return records, malformed


def sanitized_audit_record(record: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(record)
    if "argv" in sanitized and isinstance(sanitized["argv"], list):
        sanitized["argv"] = redact_argv(sanitized["argv"])
    if "error" in sanitized and isinstance(sanitized["error"], str):
        sanitized["error"] = redact_text(sanitized["error"])[:512]
    return sanitized


def count_by_key(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter(str(record.get(key, "missing")) for record in records)
    return dict(sorted(counts.items()))


def summarize_audit(records: list[dict[str, Any]],
                    malformed: list[dict[str, Any]],
                    audit_path: Path) -> dict[str, Any]:
    event_counts = count_by_key(records, "event")
    accepted: dict[str, list[dict[str, Any]]] = defaultdict(list)
    dispatched: dict[str, list[dict[str, Any]]] = defaultdict(list)
    results: dict[str, list[dict[str, Any]]] = defaultdict(list)
    result_records: list[dict[str, Any]] = []
    command_counts: Counter[str] = Counter()

    for record in records:
        event = record.get("event")
        request_id = record.get("id")
        if isinstance(record.get("command"), str):
            command_counts[str(record["command"])] += 1
        elif isinstance(record.get("argv"), list) and record["argv"]:
            command_counts[str(record["argv"][0])] += 1
        if not isinstance(request_id, str) or not request_id:
            continue
        if event == "accept":
            accepted[request_id].append(record)
        elif event == "dispatch":
            dispatched[request_id].append(record)
        elif event == "result":
            results[request_id].append(record)
            result_records.append(record)

    accepted_ids = set(accepted)
    dispatched_ids = set(dispatched)
    result_ids = set(results)
    missing_dispatch = sorted(accepted_ids - dispatched_ids)
    missing_result = sorted(dispatched_ids - result_ids)
    duplicate_results = sorted(request_id for request_id, rows in results.items() if len(rows) > 1)
    orphan_results = sorted(result_ids - dispatched_ids)
    non_ok_results = [record for record in result_records if not record.get("ok")]
    durations = [
        int(record["duration_ms"])
        for record in result_records
        if isinstance(record.get("duration_ms"), int)
    ]
    integrity_ok = (
        not malformed and
        not missing_dispatch and
        not missing_result and
        not duplicate_results and
        not orphan_results
    )

    return {
        "schema": "a90-broker-audit-report-v188",
        "audit_path": str(audit_path),
        "record_count": len(records),
        "malformed_count": len(malformed),
        "event_counts": event_counts,
        "request_counts": {
            "accepted": len(accepted_ids),
            "dispatched": len(dispatched_ids),
            "results": len(result_ids),
            "non_ok_results": len(non_ok_results),
        },
        "class_counts": count_by_key(result_records, "class"),
        "backend_counts": count_by_key(result_records, "backend"),
        "status_counts": count_by_key(result_records, "status"),
        "command_counts": dict(sorted(command_counts.items())),
        "duration_ms": {
            "min": min(durations) if durations else None,
            "max": max(durations) if durations else None,
            "avg": round(sum(durations) / len(durations), 3) if durations else None,
        },
        "integrity": {
            "ok": integrity_ok,
            "malformed": malformed,
            "missing_dispatch": missing_dispatch,
            "missing_result": missing_result,
            "duplicate_results": duplicate_results,
            "orphan_results": orphan_results,
        },
        "non_ok_results": [sanitized_audit_record(record) for record in non_ok_results[-32:]],
    }


def render_audit_markdown(summary: dict[str, Any]) -> str:
    result = "PASS" if summary["integrity"]["ok"] else "FAIL"
    lines = [
        "# A90B1 Broker Audit Report\n\n",
        f"- result: `{result}`\n",
        f"- audit_path: `{summary['audit_path']}`\n",
        f"- records: `{summary['record_count']}`\n",
        f"- malformed: `{summary['malformed_count']}`\n",
        f"- accepted: `{summary['request_counts']['accepted']}`\n",
        f"- dispatched: `{summary['request_counts']['dispatched']}`\n",
        f"- results: `{summary['request_counts']['results']}`\n",
        f"- non_ok_results: `{summary['request_counts']['non_ok_results']}`\n",
        f"- duration_ms: `{summary['duration_ms']}`\n\n",
        "## Event Counts\n\n",
    ]
    for key, value in summary["event_counts"].items():
        lines.append(f"- `{key}`: `{value}`\n")
    lines.append("\n## Status Counts\n\n")
    for key, value in summary["status_counts"].items():
        lines.append(f"- `{key}`: `{value}`\n")
    lines.append("\n## Class Counts\n\n")
    for key, value in summary["class_counts"].items():
        lines.append(f"- `{key}`: `{value}`\n")
    lines.append("\n## Integrity\n\n")
    integrity = summary["integrity"]
    for key in ("missing_dispatch", "missing_result", "duplicate_results", "orphan_results"):
        lines.append(f"- `{key}`: `{len(integrity[key])}`\n")
    if summary["non_ok_results"]:
        lines.append("\n## Non-OK Results\n\n")
        for record in summary["non_ok_results"]:
            lines.append(
                f"- id=`{record.get('id')}` status=`{record.get('status')}` "
                f"rc=`{record.get('rc')}` class=`{record.get('class')}` "
                f"backend=`{record.get('backend')}`\n"
            )
    return "".join(lines)


def cmd_report(args: argparse.Namespace) -> int:
    audit_path = args.audit if args.audit else args.runtime_dir / args.audit_name
    out_dir = args.out_dir if args.out_dir else args.runtime_dir / "audit-report"
    ensure_private_dir(out_dir)
    records, malformed = read_audit_jsonl(audit_path)
    sanitized_records = [sanitized_audit_record(record) for record in records]
    summary = summarize_audit(records, malformed, audit_path)
    write_private_json(out_dir / "broker-audit-summary.json", summary)
    write_private_json(out_dir / "broker-audit-records-redacted.json", {"records": sanitized_records})
    write_private_text(out_dir / "broker-audit-report.md", render_audit_markdown(summary))
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        result = "PASS" if summary["integrity"]["ok"] else "FAIL"
        print(
            f"{result} audit={audit_path} records={summary['record_count']} "
            f"results={summary['request_counts']['results']} "
            f"non_ok={summary['request_counts']['non_ok_results']} out={out_dir}"
        )
    return 0 if summary["integrity"]["ok"] or args.allow_integrity_fail else 1


def cmd_serve(args: argparse.Namespace) -> int:
    if args.backend == "ncm-tcpctl" and args.no_auth and not args.allow_no_auth:
        raise SystemExit("--no-auth requires --allow-no-auth for explicit legacy/negative testing")
    try:
        backend = make_backend(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    policy = BrokerPolicy(allow_operator=args.allow_operator, allow_exclusive=args.allow_exclusive)
    socket_path, audit_path = prepare_runtime_paths(args.runtime_dir, args.socket_name, args.audit_name)
    metadata = {
        "proto": PROTO,
        "backend": backend.name,
        "backend_metadata": backend.metadata(),
        "policy": policy.to_dict(),
        "socket": str(socket_path),
        "audit": str(audit_path),
    }
    write_private_json(args.runtime_dir / "broker.json", metadata)
    server = BrokerServer(backend, socket_path, audit_path, policy)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("stopping on interrupt")
        return 130
    return 0


def cmd_call(args: argparse.Namespace) -> int:
    argv = args.command
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        raise SystemExit("command is required")
    socket_path = args.socket if args.socket else args.runtime_dir / args.socket_name
    payload = build_request(args, argv)
    response = connect_and_call(socket_path, payload, args.timeout + 5.0)
    if args.json:
        print(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if response.get("text"):
            print(response["text"], end="" if response["text"].endswith("\n") else "\n")
        if response.get("error"):
            print(response["error"], file=sys.stderr)
    return 0 if response.get("ok") or args.allow_error else 1


def cmd_selftest(_: argparse.Namespace) -> int:
    temp_dir = Path(tempfile.mkdtemp(prefix="a90-broker-selftest."))
    try:
        socket_path, audit_path = prepare_runtime_paths(temp_dir, DEFAULT_SOCKET_NAME, DEFAULT_AUDIT_NAME)
        server = BrokerServer(FakeBackend(), socket_path, audit_path)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        deadline = time.monotonic() + 5.0
        while not socket_path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not socket_path.exists():
            raise RuntimeError("selftest server did not create socket")

        status_request = {
            "proto": PROTO,
            "id": "selftest-status",
            "client_id": "selftest",
            "op": "cmd",
            "argv": ["status"],
            "timeout_ms": 1000,
            "class": "observe",
        }
        status_response = connect_and_call(socket_path, status_request, 3.0)
        if not status_response.get("ok"):
            raise RuntimeError(f"status response failed: {status_response}")
        if status_response.get("class") != "observe":
            raise RuntimeError(f"unexpected status class: {status_response}")

        mountsd_request = {
            "proto": PROTO,
            "id": "selftest-mountsd",
            "client_id": "selftest",
            "op": "cmd",
            "argv": ["mountsd"],
            "timeout_ms": 1000,
            "class": "exclusive",
        }
        mountsd_response = connect_and_call(socket_path, mountsd_request, 3.0)
        if mountsd_response.get("ok") is not False or mountsd_response.get("status") != "exclusive-required":
            raise RuntimeError(f"bare mountsd was not blocked as exclusive: {mountsd_response}")

        menu_request = {
            "proto": PROTO,
            "id": "selftest-menu",
            "client_id": "selftest",
            "op": "cmd",
            "argv": ["menu"],
            "timeout_ms": 1000,
            "class": "operator-action",
        }
        menu_response = connect_and_call(socket_path, menu_request, 3.0)
        if menu_response.get("ok") is not False or menu_response.get("status") != "operator-required":
            raise RuntimeError(f"menu was not blocked as operator-action: {menu_response}")

        sensitive_cat_request = {
            "proto": PROTO,
            "id": "selftest-sensitive-cat",
            "client_id": "selftest",
            "op": "cmd",
            "argv": ["cat", DEFAULT_TOKEN_PATH],
            "timeout_ms": 1000,
            "class": "operator-action",
        }
        sensitive_cat_response = connect_and_call(socket_path, sensitive_cat_request, 3.0)
        if (sensitive_cat_response.get("ok") is not False or
                sensitive_cat_response.get("status") != "sensitive-path-denied"):
            raise RuntimeError(f"sensitive cat was not blocked: {sensitive_cat_response}")

        blocked_request = {
            "proto": PROTO,
            "id": "selftest-reboot",
            "client_id": "selftest",
            "op": "cmd",
            "argv": ["reboot"],
            "timeout_ms": 1000,
            "class": "rebind-destructive",
        }
        blocked_response = connect_and_call(socket_path, blocked_request, 3.0)
        if blocked_response.get("status") != "operator-required":
            raise RuntimeError(f"reboot was not blocked: {blocked_response}")

        records, malformed = read_audit_jsonl(audit_path)
        summary = summarize_audit(records, malformed, audit_path)
        if not summary["integrity"]["ok"]:
            raise RuntimeError(f"audit integrity failed: {summary['integrity']}")
        if summary["request_counts"]["results"] != 5:
            raise RuntimeError(f"unexpected audit result count: {summary['request_counts']}")

        print("a90_broker selftest: PASS")
        return 0
    finally:
        try:
            socket_file = temp_dir / DEFAULT_SOCKET_NAME
            if socket_file.exists() and not socket_file.is_symlink():
                socket_file.unlink()
            audit_file = temp_dir / DEFAULT_AUDIT_NAME
            if audit_file.exists() and not audit_file.is_symlink():
                audit_file.unlink()
            meta_file = temp_dir / "broker.json"
            if meta_file.exists() and not meta_file.is_symlink():
                meta_file.unlink()
            report_dir = temp_dir / "audit-report"
            if report_dir.exists() and not report_dir.is_symlink():
                for child in report_dir.iterdir():
                    if child.is_file() and not child.is_symlink():
                        child.unlink()
                report_dir.rmdir()
            temp_dir.rmdir()
        except OSError:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A90B1 host-local command broker.")
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    serve = subparsers.add_parser("serve", help="run the host-local broker")
    serve.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    serve.add_argument("--socket-name", default=DEFAULT_SOCKET_NAME)
    serve.add_argument("--audit-name", default=DEFAULT_AUDIT_NAME)
    serve.add_argument("--backend", choices=("acm-cmdv1", "fake", "ncm-tcpctl"), default="acm-cmdv1")
    serve.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    serve.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    serve.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    serve.add_argument("--tcp-port", type=int, default=DEFAULT_TCP_PORT)
    serve.add_argument("--tcp-timeout", type=float, default=DEFAULT_TCP_TIMEOUT)
    serve.add_argument("--token")
    serve.add_argument("--token-path", default=DEFAULT_TOKEN_PATH)
    serve.add_argument("--no-auth", action="store_true")
    serve.add_argument(
        "--allow-no-auth",
        action="store_true",
        help="explicitly allow legacy unauthenticated ncm-tcpctl mode for negative tests",
    )
    serve.add_argument(
        "--allow-operator",
        action="store_true",
        help="allow operator-action commands such as menu/autohud through the broker",
    )
    serve.add_argument(
        "--allow-exclusive",
        action="store_true",
        help="allow exclusive root-control commands such as run/cpustress through the broker",
    )
    serve.set_defaults(func=cmd_serve)

    call = subparsers.add_parser("call", help="send one command through the broker")
    call.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    call.add_argument("--socket-name", default=DEFAULT_SOCKET_NAME)
    call.add_argument("--socket", type=Path)
    call.add_argument("--timeout", type=float, default=10.0)
    call.add_argument("--request-id")
    call.add_argument("--client-id", default=f"cli:{os.getpid()}")
    call.add_argument("--class", dest="command_class")
    call.add_argument("--json", action="store_true")
    call.add_argument("--allow-error", action="store_true")
    call.add_argument("command", nargs=argparse.REMAINDER)
    call.set_defaults(func=cmd_call)

    report = subparsers.add_parser("report", help="summarize and validate broker audit JSONL")
    report.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    report.add_argument("--audit-name", default=DEFAULT_AUDIT_NAME)
    report.add_argument("--audit", type=Path)
    report.add_argument("--out-dir", type=Path)
    report.add_argument("--json", action="store_true")
    report.add_argument("--allow-integrity-fail", action="store_true")
    report.set_defaults(func=cmd_report)

    selftest = subparsers.add_parser("selftest", help="run broker fake-backend selftest")
    selftest.set_defaults(func=cmd_selftest)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
