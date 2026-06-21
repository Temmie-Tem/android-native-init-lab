#!/usr/bin/env python3

import argparse
import json
import os
import re
import shlex
import socket
import sys
import time
from dataclasses import dataclass

from a90_serial_lock import SerialBridgeLock, SerialBridgeLockBusy


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
CMDV1_RETRY_INTERVAL_SEC = 0.5
BRIDGE_SERIAL_MISSING_TEXT = "serial device is not connected"
BRIDGE_BUSY_TEXT = "busy: another client is active"
INPUT_MODE_ENV = "A90CTL_INPUT_MODE"
INPUT_CHAR_DELAY_ENV = "A90CTL_INPUT_CHAR_DELAY_SEC"
END_RE = re.compile(r"^A90P1 END (?P<fields>.+)$", re.MULTILINE)
BEGIN_RE = re.compile(r"^A90P1 BEGIN (?P<fields>.+)$", re.MULTILINE)
COMMAND_NAME_RE = re.compile(r"^[A-Za-z0-9_.+-]+$")
SAFE_RETRY_COMMANDS = {
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
    "wifi",
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
    "cat",
    "stat",
    "screenapp",
}


@dataclass
class ProtocolResult:
    begin: dict[str, str]
    end: dict[str, str]
    text: str

    @property
    def rc(self) -> int:
        return int(self.end.get("rc", "1"), 0)

    @property
    def status(self) -> str:
        return self.end.get("status", "missing")


def log(message: str) -> None:
    print(f"[a90ctl] {message}", file=sys.stderr, flush=True)


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in text.split():
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        fields[key] = value
    return fields


def shell_command_to_argv(command: str) -> list[str] | None:
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    return argv or None


def can_use_legacy_cmdv1_arg(arg: str) -> bool:
    if not arg or arg.startswith("#"):
        return False
    return not any(ch.isspace() or ch in "\r\n" for ch in arg)


def encode_cmdv1x_arg(arg: str) -> str:
    if "\x00" in arg:
        raise RuntimeError("cmdv1x cannot encode NUL bytes")
    data = arg.encode("utf-8")
    return f"{len(data)}:{data.hex()}"


def encode_cmdv1_line(command: list[str]) -> str:
    if not command:
        raise RuntimeError("cmdv1 command is required")
    if not command[0] or not COMMAND_NAME_RE.match(command[0]):
        raise RuntimeError(f"cmdv1 command name cannot be encoded safely: {command[0]!r}")
    if any("\x00" in arg for arg in command):
        raise RuntimeError("cmdv1 cannot encode NUL bytes")
    if all(can_use_legacy_cmdv1_arg(arg) for arg in command):
        return "cmdv1 " + " ".join(command)
    return "cmdv1x " + " ".join(encode_cmdv1x_arg(arg) for arg in command)


def double_input_line(line: str) -> str:
    return "".join(ch * 2 for ch in line)


def encode_wire_line(line: str, input_mode: str | None = None) -> str:
    mode = input_mode or os.environ.get(INPUT_MODE_ENV, "normal")
    if mode == "double":
        return double_input_line(line)
    if mode in {"", "normal", "slow"}:
        return line
    raise RuntimeError(f"unsupported {INPUT_MODE_ENV}={mode!r}")


def has_prompt_after_last_end(data: bytearray) -> bool:
    end_index = data.rfind(b"A90P1 END ")
    if end_index < 0:
        return False
    tail = data[end_index:]
    return b"\na90:/#" in tail or b"\ra90:/#" in tail


def read_until(sock: socket.socket,
               markers: tuple[bytes, ...],
               timeout_sec: float,
               *,
               require_prompt_after_end: bool = False,
               post_marker_drain_sec: float = 0.15) -> bytes:
    deadline = time.monotonic() + timeout_sec
    data = bytearray()
    while time.monotonic() < deadline:
        try:
            chunk = sock.recv(8192)
        except socket.timeout:
            continue
        if not chunk:
            break
        data.extend(chunk)
        if any(marker in data for marker in markers):
            if require_prompt_after_end and b"A90P1 END " in data and not has_prompt_after_last_end(data):
                continue
            if post_marker_drain_sec > 0.0:
                time.sleep(post_marker_drain_sec)
                try:
                    data.extend(sock.recv(8192))
                except socket.timeout:
                    pass
            break
    return bytes(data)


def bridge_exchange(host: str,
                    port: int,
                    line: str,
                    timeout_sec: float,
                    markers: tuple[bytes, ...],
                    *,
                    input_mode: str | None = None,
                    require_prompt_after_end: bool = False,
                    post_marker_drain_sec: float = 0.15) -> str:
    deadline = time.monotonic() + timeout_sec
    wire_line = encode_wire_line(line, input_mode=input_mode)
    mode = input_mode or os.environ.get(INPUT_MODE_ENV, "normal")
    with SerialBridgeLock(timeout_sec=timeout_sec, purpose=f"a90ctl:{line.split(' ', 1)[0]}"):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SerialBridgeLockBusy("serial bridge transaction lock wait exhausted command timeout")
        connect_timeout = min(3.0, max(0.1, remaining))
        with socket.create_connection((host, port), timeout=connect_timeout) as sock:
            sock.settimeout(0.25)
            prefix = "" if mode in {"double", "slow"} else "\n"
            payload = prefix + wire_line + "\n"
            if mode == "slow":
                delay = float(os.environ.get(INPUT_CHAR_DELAY_ENV, "0.02"))
                for ch in payload:
                    sock.sendall(ch.encode("utf-8"))
                    time.sleep(delay)
            else:
                sock.sendall(payload.encode("utf-8"))
            data = read_until(
                sock,
                markers,
                max(0.1, deadline - time.monotonic()),
                require_prompt_after_end=require_prompt_after_end,
                post_marker_drain_sec=post_marker_drain_sec,
            )
    return data.decode("utf-8", errors="replace")


def should_retry_cmdv1_exchange(text: str) -> bool:
    if text.strip() == "" or BRIDGE_SERIAL_MISSING_TEXT in text or BRIDGE_BUSY_TEXT in text:
        return True
    if os.environ.get(INPUT_MODE_ENV) in {"double", "slow"} and "[err] unknown command:" in text:
        return True
    return False


def sleep_before_retry(deadline: float) -> None:
    remaining = deadline - time.monotonic()
    if remaining > 0:
        time.sleep(min(CMDV1_RETRY_INTERVAL_SEC, remaining))


def parse_protocol_output(text: str) -> ProtocolResult:
    begin_matches = list(BEGIN_RE.finditer(text))
    end_matches = list(END_RE.finditer(text))
    begin_match = begin_matches[-1] if begin_matches else None
    end_match = end_matches[-1] if end_matches else None
    if end_match is None:
        raise RuntimeError(f"A90P1 END marker not found\n{text}")
    end_fields = parse_fields(end_match.group("fields"))
    if begin_match is not None:
        matching_begin = None
        for candidate in reversed(begin_matches):
            begin_fields = parse_fields(candidate.group("fields"))
            if (begin_fields.get("seq") == end_fields.get("seq") and
                    begin_fields.get("cmd") == end_fields.get("cmd")):
                matching_begin = candidate
                break
        if matching_begin is not None:
            begin_match = matching_begin
    return ProtocolResult(
        begin=parse_fields(begin_match.group("fields")) if begin_match else {},
        end=end_fields,
        text=text,
    )


def validate_protocol_command(result: ProtocolResult, command: list[str]) -> None:
    expected = command[0] if command else ""
    actual = result.end.get("cmd", "")
    if expected and actual and actual != expected:
        raise RuntimeError(
            f"A90P1 command mismatch expected={expected!r} actual={actual!r}\n"
            f"{result.text}"
        )


def command_allows_retry(command: list[str]) -> bool:
    return bool(command) and command[0] in SAFE_RETRY_COMMANDS


def run_cmdv1(args: argparse.Namespace, command: list[str]) -> ProtocolResult:
    return run_cmdv1_command(
        args.host,
        args.port,
        args.timeout,
        command,
        retry_unsafe=args.retry_unsafe,
    )


def run_cmdv1_command(host: str,
                      port: int,
                      timeout_sec: float,
                      command: list[str],
                      *,
                      retry_unsafe: bool = False,
                      require_prompt_after_end: bool = True,
                      post_marker_drain_sec: float = 0.15) -> ProtocolResult:
    deadline = time.monotonic() + timeout_sec
    last_error: OSError | None = None
    last_text = ""
    allow_retry = retry_unsafe or command_allows_retry(command)

    line = encode_cmdv1_line(command)
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        try:
            markers = (b"A90P1 END ",)
            if allow_retry and os.environ.get(INPUT_MODE_ENV) in {"double", "slow"}:
                markers = (b"A90P1 END ", b"[err] unknown command:")
            text = bridge_exchange(
                host,
                port,
                line,
                remaining,
                markers=markers,
                require_prompt_after_end=require_prompt_after_end,
                post_marker_drain_sec=post_marker_drain_sec,
            )
        except OSError as exc:
            last_error = exc
            if not allow_retry:
                raise
            sleep_before_retry(deadline)
            continue

        if END_RE.search(text) is not None:
            result = parse_protocol_output(text)
            try:
                validate_protocol_command(result, command)
            except RuntimeError as exc:
                if not allow_retry or os.environ.get(INPUT_MODE_ENV) not in {"double", "slow"}:
                    raise
                last_text = str(exc)
                sleep_before_retry(deadline)
                continue
            return result
        if BRIDGE_BUSY_TEXT in text:
            last_text = text
            if not allow_retry:
                raise RuntimeError(
                    "bridge busy response received after unsafe command send; "
                    "not retrying command without retry_unsafe\n"
                    f"{text}"
                )
            sleep_before_retry(deadline)
            continue
        if not allow_retry:
            return parse_protocol_output(text)
        if not should_retry_cmdv1_exchange(text):
            return parse_protocol_output(text)

        last_text = text
        sleep_before_retry(deadline)

    detail = f"A90P1 END marker not found before timeout ({timeout_sec:.1f}s)"
    if last_error is not None:
        detail += f"\nlast socket error: {last_error}"
    if last_text:
        detail += f"\nlast bridge output:\n{last_text}"
    raise RuntimeError(detail)


def send_hide(args: argparse.Namespace) -> None:
    text = bridge_exchange(
        args.host,
        args.port,
        "hide",
        min(args.timeout, 8.0),
        markers=(b"[busy]", b"[done]", b"[err]"),
        input_mode=args.input_mode,
    )
    if args.verbose:
        print(text, end="" if text.endswith("\n") else "\n", file=sys.stderr)


def result_to_json(result: ProtocolResult) -> str:
    return json.dumps(
        {
            "begin": result.begin,
            "end": result.end,
            "rc": result.rc,
            "status": result.status,
            "text": result.text,
        },
        ensure_ascii=False,
        indent=2,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one native-init shell command through cmdv1/A90P1 framing."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--allow-error", action="store_true")
    parser.add_argument("--hide-on-busy", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--input-mode",
        choices=("normal", "double", "slow"),
        default=os.environ.get(INPUT_MODE_ENV, "normal"),
        help="wire encoding for serial-input contention; 'double' sends each character twice",
    )
    parser.add_argument(
        "--retry-unsafe",
        action="store_true",
        help="allow reconnect retry for non-observation commands; default retries only read-only commands",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("command is required, e.g. a90ctl.py status")

    os.environ[INPUT_MODE_ENV] = args.input_mode
    result = run_cmdv1(args, command)
    if args.hide_on_busy and result.status == "busy":
        log("command was busy; sending hide and retrying once")
        send_hide(args)
        result = run_cmdv1(args, command)

    if args.as_json:
        print(result_to_json(result))
    elif not args.quiet:
        print(result.text, end="" if result.text.endswith("\n") else "\n")

    if result.rc != 0 and not args.allow_error:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
