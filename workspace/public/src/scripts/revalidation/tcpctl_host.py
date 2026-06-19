#!/usr/bin/env python3

import argparse
import hashlib
import os
import posixpath
import re
import shlex
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

add_legacy_revalidation_path(repo_root())

from a90ctl import ProtocolResult, run_cmdv1_command, shell_command_to_argv
from a90harness.evidence import workspace_private_input_path


ROOT_DIR = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 54321
DEFAULT_DEVICE_IP = "192.168.7.2"
DEFAULT_TCP_PORT = 2325
DEFAULT_TRANSFER_PORT = 18083
DEFAULT_DEVICE_BINARY = "/bin/a90_tcpctl"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_LOCAL_BINARY = workspace_private_input_path(
    "external_tools", "userland", "bin", "a90_tcpctl-aarch64-static"
)
DEFAULT_IDLE_TIMEOUT = 60
DEFAULT_MAX_CLIENTS = 8
DEFAULT_SOAK_MAX_CLIENTS = 0
DEFAULT_TCPCTL_TOKEN_PATH = "/cache/native-init-tcpctl.token"
DEFAULT_TOKEN_COMMAND = "netservice token show"
CMDV1_END_MISSING_TEXT = "A90P1 END marker not found"
TOKEN_RE = re.compile(r"tcpctl_token=([0-9A-Fa-f]{32})")
SAFE_DEVICE_PATH_RE = re.compile(r"^[A-Za-z0-9_./-]+$")
INSTALL_ALLOWED_PREFIXES = (
    "/cache/bin/",
    "/cache/a90-acdb-setcal-replay-",
    "/cache/a90-runtime/bin/",
    "/cache/a90-runtime/pkg/",
    "/mnt/sdext/a90/bin/",
)


def log(message: str) -> None:
    print(f"[tcpctl] {message}", file=sys.stderr, flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        while True:
            chunk = fp.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def validate_install_target(path: str) -> None:
    parts = path.split("/")

    if not path.startswith("/") or not SAFE_DEVICE_PATH_RE.fullmatch(path):
        raise RuntimeError(f"unsafe device install path: {path}")
    if any(part == ".." for part in parts):
        raise RuntimeError(f"unsafe device install path: {path}")
    if not any(path.startswith(prefix) for prefix in INSTALL_ALLOWED_PREFIXES):
        raise RuntimeError(
            "refusing to install outside runtime/cache helper roots: "
            f"{path} (use /cache/bin, /cache/a90-acdb-setcal-replay-*, "
            "/cache/a90-runtime/bin, /cache/a90-runtime/pkg, or /mnt/sdext/a90/bin)"
        )


def bridge_command(host: str,
                   port: int,
                   command: str,
                   timeout_sec: float,
                   markers: tuple[bytes, ...] = (b"[done]", b"[err]", b"[busy]")) -> str:
    deadline = time.monotonic() + timeout_sec
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2.0) as sock:
                sock.settimeout(0.25)
                sock.sendall(("\n" + command + "\n").encode())
                data = bytearray()
                read_deadline = time.monotonic() + min(10.0, max(3.0, timeout_sec))
                while time.monotonic() < read_deadline:
                    try:
                        chunk = sock.recv(8192)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    data.extend(chunk)
                    if any(marker in data for marker in markers):
                        time.sleep(0.2)
                        try:
                            data.extend(sock.recv(8192))
                        except socket.timeout:
                            pass
                        return data.decode("utf-8", errors="replace")
        except OSError as exc:
            last_error = exc

        time.sleep(0.5)

    raise RuntimeError(f"bridge command timeout for {command!r}: {last_error}")


def cmdv1_unavailable(exc: Exception) -> bool:
    if isinstance(exc, OSError):
        return True
    text = str(exc)
    if "cmdv1 cannot safely encode command" in text:
        return True
    if "serial device is not connected" in text:
        return True
    if "unknown command: cmdv1" in text or "unknown command: cmdv1x" in text:
        return True
    return False


def run_device_cmdv1(args: argparse.Namespace,
                     command: str,
                     timeout_sec: float) -> ProtocolResult:
    argv = shell_command_to_argv(command)
    if argv is None:
        raise RuntimeError(f"cmdv1 cannot parse shell command: {command!r}")
    return run_cmdv1_command(args.bridge_host, args.bridge_port, timeout_sec, argv)


def device_command(args: argparse.Namespace,
                   command: str,
                   *,
                   timeout: float | None = None,
                   allow_error: bool = False,
                   use_cmdv1: bool = True) -> str:
    timeout_sec = args.bridge_timeout if timeout is None else timeout
    cmdv1_enabled = use_cmdv1 and args.device_protocol != "raw"
    cmdv1_failed_open = False

    for attempt in range(1, args.busy_retries + 1):
        if cmdv1_enabled and not cmdv1_failed_open:
            try:
                result = run_device_cmdv1(args, command, timeout_sec)
            except RuntimeError as exc:
                if args.device_protocol == "cmdv1" or not cmdv1_unavailable(exc):
                    raise
                log(f"cmdv1 unavailable for {command!r}; falling back to raw bridge")
                cmdv1_failed_open = True
            else:
                if result.status != "busy":
                    if (result.rc != 0 or result.status != "ok") and not allow_error:
                        raise RuntimeError(
                            f"device command failed: {command} "
                            f"rc={result.rc} status={result.status}\n{result.text}"
                        )
                    return result.text

                print(result.text, end="" if result.text.endswith("\n") else "\n")
                log(f"auto menu active; requesting hide before retry {attempt}/{args.busy_retries}")
                best_effort_hide_menu(args)
                time.sleep(args.busy_retry_sleep)
                continue

        output = bridge_command(
            args.bridge_host,
            args.bridge_port,
            command,
            timeout_sec,
        )
        if "[busy]" not in output:
            if "[err]" in output and not allow_error:
                raise RuntimeError(f"device command failed: {command}\n{output}")
            return output

        print(output, end="" if output.endswith("\n") else "\n")
        log(f"auto menu active; requesting hide before retry {attempt}/{args.busy_retries}")
        best_effort_hide_menu(args)
        time.sleep(args.busy_retry_sleep)

    raise RuntimeError(f"device command stayed busy after retries: {command}")


def best_effort_hide_menu(args: argparse.Namespace) -> None:
    try:
        output = bridge_command(
            args.bridge_host,
            args.bridge_port,
            "hide",
            args.bridge_timeout,
            markers=(b"[busy]", b"[done]", b"[err]"),
        )
    except RuntimeError:
        return

    if "[busy]" in output:
        log("auto menu hide requested")
        time.sleep(args.menu_hide_sleep)


def parse_tcpctl_token(output: str) -> str:
    match = TOKEN_RE.search(output)
    if not match:
        raise RuntimeError(f"tcpctl token was not found in output:\n{output}")
    return match.group(1)


def tcpctl_command_requires_auth(command: str) -> bool:
    word = command.lstrip().split(maxsplit=1)[0] if command.strip() else ""
    return word in {"run", "shutdown"}


def get_tcpctl_token(args: argparse.Namespace) -> str:
    cached = getattr(args, "_tcpctl_token", None)
    if cached:
        return cached
    if args.token:
        args._tcpctl_token = args.token
        return args.token
    output = device_command(args, args.token_command, timeout=args.bridge_timeout)
    token = parse_tcpctl_token(output)
    args._tcpctl_token = token
    return token


class BridgeRunThread(threading.Thread):
    def __init__(self, args: argparse.Namespace, command: str, *, echo: bool = False) -> None:
        super().__init__(daemon=True)
        self.args = args
        self.command = command
        self.echo = echo
        self.buffer = bytearray()
        self.ready = threading.Event()
        self.done = threading.Event()
        self.error: Exception | None = None

    def run(self) -> None:
        try:
            with socket.create_connection(
                (self.args.bridge_host, self.args.bridge_port),
                timeout=self.args.connect_timeout,
            ) as sock:
                sock.settimeout(0.25)
                sock.sendall(("\n" + self.command + "\n").encode())
                while True:
                    try:
                        chunk = sock.recv(8192)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    self.buffer.extend(chunk)
                    if self.echo:
                        sys.stdout.buffer.write(chunk)
                        sys.stdout.buffer.flush()
                    if b"tcpctl: listening" in self.buffer:
                        self.ready.set()
                    if (b"[done] run" in self.buffer or
                            b"[err] run" in self.buffer or
                            b"[busy]" in self.buffer):
                        break
        except Exception as exc:
            self.error = exc
        finally:
            self.done.set()

    def text(self) -> str:
        return self.buffer.decode("utf-8", errors="replace")


def tcpctl_request(args: argparse.Namespace, command: str, *, timeout: float | None = None) -> str:
    timeout_sec = args.tcp_timeout if timeout is None else timeout
    payload = command.rstrip("\n") + "\n"
    if not args.no_auth and tcpctl_command_requires_auth(command):
        payload = f"auth {get_tcpctl_token(args)}\n{payload}"
    with socket.create_connection((args.device_ip, args.tcp_port), timeout=timeout_sec) as sock:
        sock.settimeout(0.5)
        sock.sendall(payload.encode())
        data = bytearray()
        deadline = time.monotonic() + timeout_sec

        while time.monotonic() < deadline:
            try:
                chunk = sock.recv(8192)
            except socket.timeout:
                continue
            if not chunk:
                break
            data.extend(chunk)

        return data.decode("utf-8", errors="replace")


def tcpctl_expect_ok(args: argparse.Namespace, command: str) -> str:
    output = tcpctl_request(args, command)
    if "\nOK" not in output and not output.rstrip().endswith("OK"):
        raise RuntimeError(f"tcpctl command did not end with OK: {command}\n{output}")
    return output


def tcpctl_run_line(argv: list[str]) -> str:
    return "run " + " ".join(shlex.quote(part) for part in argv)


def tcpctl_install_command(args: argparse.Namespace,
                           command: str,
                           *,
                           timeout: float | None = None,
                           allow_error: bool = False) -> str:
    output = tcpctl_request(args, command, timeout=timeout)
    if "\nOK" not in output and not output.rstrip().endswith("OK"):
        if allow_error and "\nERR" in output:
            return output
        raise RuntimeError(f"tcpctl install command did not end with OK: {command}\n{output}")
    return output


def host_ping(args: argparse.Namespace, count: int) -> str:
    result = subprocess.run(
        ["ping", "-c", str(count), "-W", "2", args.device_ip],
        check=False,
        text=True,
        capture_output=True,
        timeout=max(5.0, count * 3.0),
    )
    output = result.stdout
    if result.stderr:
        output += result.stderr
    if result.returncode != 0:
        raise RuntimeError(f"ping failed rc={result.returncode}\n{output}")
    return output


def wait_for_tcpctl(args: argparse.Namespace, timeout_sec: float) -> str:
    deadline = time.monotonic() + timeout_sec
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            output = tcpctl_request(args, "ping", timeout=2.0)
            if "pong" in output and "OK" in output:
                return output
        except OSError as exc:
            last_error = exc
        time.sleep(0.5)

    raise RuntimeError(f"tcpctl did not become ready: {last_error}")


def tcpctl_listen_command(args: argparse.Namespace) -> str:
    return (
        f"run {args.device_binary} listen "
        f"{args.device_ip} {args.tcp_port} {args.idle_timeout} "
        f"{args.max_clients} {args.token_path if not args.no_auth else '-'}"
    )


def command_start(args: argparse.Namespace) -> int:
    best_effort_hide_menu(args)
    if not args.no_auth:
        get_tcpctl_token(args)
    command = tcpctl_listen_command(args)
    log(f"starting via bridge: {command}")
    runner = BridgeRunThread(args, command, echo=True)
    runner.start()
    try:
        while not runner.done.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        log("interrupt: requesting tcpctl shutdown")
        try:
            print(tcpctl_request(args, "shutdown"), end="")
        except Exception as exc:
            log(f"shutdown request failed: {exc}")
        runner.join(args.bridge_timeout)
        return 130

    if runner.error is not None:
        raise RuntimeError(f"bridge run failed: {runner.error}")
    return 0


def command_call(args: argparse.Namespace) -> int:
    if not args.line:
        raise SystemExit("call requires a command line")
    command = " ".join(args.line)
    print(tcpctl_request(args, command), end="")
    return 0


def command_ping(args: argparse.Namespace) -> int:
    print(tcpctl_request(args, "ping"), end="")
    return 0


def command_version(args: argparse.Namespace) -> int:
    print(tcpctl_request(args, "version"), end="")
    return 0


def command_status(args: argparse.Namespace) -> int:
    print(tcpctl_request(args, "status"), end="")
    return 0


def command_run(args: argparse.Namespace) -> int:
    if not args.run_args:
        raise SystemExit("run requires an absolute path and optional args")
    run_args = args.run_args
    if run_args and run_args[0] == "--":
        run_args = run_args[1:]
    if not run_args:
        raise SystemExit("run requires an absolute path and optional args")
    command = "run " + " ".join(shlex.quote(part) for part in run_args)
    print(tcpctl_request(args, command), end="")
    return 0


def command_stop(args: argparse.Namespace) -> int:
    print(tcpctl_request(args, "shutdown"), end="")
    return 0


def command_install(args: argparse.Namespace) -> int:
    if args.install_control_channel == "tcpctl":
        return command_install_via_tcpctl(args)

    local_binary = Path(args.local_binary)
    target = args.device_binary
    target_dir = posixpath.dirname(target)
    target_name = posixpath.basename(target)
    tmp_target = f"{target_dir}/.{target_name}.tmp.{os.getpid()}.{int(time.time())}"

    if not local_binary.exists():
        raise FileNotFoundError(local_binary)
    validate_install_target(target)

    local_hash = sha256_file(local_binary)
    best_effort_hide_menu(args)
    receive_command = (
        f"run {args.toybox} netcat -l -p {args.transfer_port} "
        f"{args.toybox} dd of={tmp_target} bs=4096"
    )
    log(f"device receive command: {receive_command}")

    try:
        mkdir_output = device_command(
            args,
            f"mkdir {target_dir}",
            timeout=args.bridge_timeout,
            allow_error=True,
        )
        if mkdir_output:
            print(mkdir_output, end="" if mkdir_output.endswith("\n") else "\n")

        cleanup_output = device_command(
            args,
            f"run {args.toybox} rm -f {tmp_target}",
            timeout=args.bridge_timeout,
            allow_error=True,
        )
        if cleanup_output:
            print(cleanup_output, end="" if cleanup_output.endswith("\n") else "\n")

        runner = BridgeRunThread(args, receive_command, echo=args.verbose)
        runner.start()
        time.sleep(args.transfer_delay)

        with socket.create_connection((args.device_ip, args.transfer_port), timeout=args.connect_timeout) as sock:
            with local_binary.open("rb") as fp:
                while True:
                    chunk = fp.read(1024 * 1024)
                    if not chunk:
                        break
                    sock.sendall(chunk)
            sock.shutdown(socket.SHUT_WR)

        runner.join(args.transfer_timeout)
        if runner.is_alive():
            raise RuntimeError("device transfer did not finish")
        if runner.error is not None:
            raise RuntimeError(f"bridge transfer failed: {runner.error}")
        if "[done] run" not in runner.text():
            raise RuntimeError(f"device transfer did not report done:\n{runner.text()}")

        print(runner.text(), end="" if runner.text().endswith("\n") else "\n")
        chmod_output = device_command(
            args,
            f"run {args.toybox} chmod 755 {tmp_target}",
            timeout=args.bridge_timeout,
        )
        print(chmod_output, end="" if chmod_output.endswith("\n") else "\n")
        sha_output = device_command(
            args,
            f"run {args.toybox} sha256sum {tmp_target}",
            timeout=args.bridge_timeout,
        )
        print(sha_output, end="" if sha_output.endswith("\n") else "\n")
        if local_hash not in sha_output:
            raise RuntimeError(f"device tmp sha256 did not match local {local_hash}")
        mv_output = device_command(
            args,
            f"run {args.toybox} mv -f {tmp_target} {target}",
            timeout=args.bridge_timeout,
        )
        print(mv_output, end="" if mv_output.endswith("\n") else "\n")
    except Exception:
        try:
            device_command(
                args,
                f"run {args.toybox} rm -f {tmp_target}",
                timeout=args.bridge_timeout,
                allow_error=True,
            )
        except Exception as cleanup_exc:
            log(f"cleanup failed for {tmp_target}: {cleanup_exc}")
        raise

    log(f"installed {target} sha256={local_hash}")
    return 0


def command_install_via_tcpctl(args: argparse.Namespace) -> int:
    local_binary = Path(args.local_binary)
    target = args.device_binary
    target_dir = posixpath.dirname(target)
    target_name = posixpath.basename(target)
    tmp_target = f"{target_dir}/.{target_name}.tmp.{os.getpid()}.{int(time.time())}"
    transfer_output: dict[str, str] = {}
    transfer_error: dict[str, Exception] = {}

    if not local_binary.exists():
        raise FileNotFoundError(local_binary)
    validate_install_target(target)

    local_hash = sha256_file(local_binary)
    tcpctl_expect_ok(args, "ping")
    mkdir_output = tcpctl_install_command(
        args,
        tcpctl_run_line([args.toybox, "mkdir", "-p", target_dir]),
        timeout=args.tcp_timeout,
    )
    print(mkdir_output, end="" if mkdir_output.endswith("\n") else "\n")
    cleanup_output = tcpctl_install_command(
        args,
        tcpctl_run_line([args.toybox, "rm", "-f", tmp_target]),
        timeout=args.tcp_timeout,
        allow_error=True,
    )
    print(cleanup_output, end="" if cleanup_output.endswith("\n") else "\n")

    receive_command = tcpctl_run_line([
        args.toybox,
        "netcat",
        "-l",
        "-p",
        str(args.transfer_port),
        args.toybox,
        "dd",
        f"of={tmp_target}",
        "bs=4096",
    ])
    log(f"device receive command via tcpctl: {receive_command}")

    def receiver() -> None:
        try:
            transfer_output["text"] = tcpctl_request(
                args,
                receive_command,
                timeout=args.transfer_timeout + args.transfer_delay + 10.0,
            )
        except Exception as exc:  # noqa: BLE001 - host install reports full context
            transfer_error["error"] = exc

    thread = threading.Thread(target=receiver, daemon=True)
    thread.start()
    time.sleep(args.transfer_delay)

    with socket.create_connection((args.device_ip, args.transfer_port), timeout=args.connect_timeout) as sock:
        with local_binary.open("rb") as fp:
            while True:
                chunk = fp.read(1024 * 1024)
                if not chunk:
                    break
                sock.sendall(chunk)
        sock.shutdown(socket.SHUT_WR)

    thread.join(args.transfer_timeout + args.transfer_delay + 15.0)
    if thread.is_alive():
        raise RuntimeError("device transfer did not finish")
    if transfer_error:
        raise RuntimeError(f"tcpctl transfer failed: {transfer_error['error']}")
    output = transfer_output.get("text", "")
    if "\nOK" not in output and not output.rstrip().endswith("OK"):
        raise RuntimeError(f"device transfer did not report OK:\n{output}")
    print(output, end="" if output.endswith("\n") else "\n")

    chmod_output = tcpctl_install_command(
        args,
        tcpctl_run_line([args.toybox, "chmod", "755", tmp_target]),
        timeout=args.tcp_timeout,
    )
    print(chmod_output, end="" if chmod_output.endswith("\n") else "\n")
    sha_output = tcpctl_install_command(
        args,
        tcpctl_run_line([args.toybox, "sha256sum", tmp_target]),
        timeout=args.tcp_timeout,
    )
    print(sha_output, end="" if sha_output.endswith("\n") else "\n")
    if local_hash not in sha_output:
        raise RuntimeError(f"device tmp sha256 did not match local {local_hash}")
    mv_output = tcpctl_install_command(
        args,
        tcpctl_run_line([args.toybox, "mv", "-f", tmp_target, target]),
        timeout=args.tcp_timeout,
    )
    print(mv_output, end="" if mv_output.endswith("\n") else "\n")
    log(f"installed {target} sha256={local_hash}")
    return 0


def command_smoke(args: argparse.Namespace) -> int:
    if args.install_first:
        command_install(args)

    best_effort_hide_menu(args)
    if not args.no_auth:
        get_tcpctl_token(args)
    runner = BridgeRunThread(args, tcpctl_listen_command(args), echo=args.verbose)
    runner.start()
    wait_for_tcpctl(args, args.ready_timeout)

    checks = [
        ("ping", "ping"),
        ("version", "version"),
        ("status", "status"),
        ("run-uname", f"run {args.toybox} uname -a"),
        ("run-ifconfig", f"run {args.toybox} ifconfig ncm0"),
    ]
    for label, command in checks:
        print(f"--- {label} ---")
        output = tcpctl_expect_ok(args, command)
        print(output, end="" if output.endswith("\n") else "\n")

    print("--- shutdown ---")
    shutdown_output = tcpctl_expect_ok(args, "shutdown")
    print(shutdown_output, end="" if shutdown_output.endswith("\n") else "\n")

    runner.join(args.bridge_timeout)
    if runner.is_alive():
        raise RuntimeError("tcpctl serial run did not finish after shutdown")
    if runner.error is not None:
        raise RuntimeError(f"bridge run failed: {runner.error}")

    print("--- serial-run ---")
    print(runner.text(), end="" if runner.text().endswith("\n") else "\n")
    if "[done] run" not in runner.text():
        raise RuntimeError("tcpctl serial run did not finish cleanly")

    print("--- bridge-version ---")
    bridge_output = device_command(
        args,
        "version",
        timeout=args.bridge_timeout,
    )
    print(bridge_output, end="" if bridge_output.endswith("\n") else "\n")

    print("--- ncm-ping ---")
    print(host_ping(args, 3), end="")

    return 0


def command_soak(args: argparse.Namespace) -> int:
    if args.install_first:
        command_install(args)

    args.max_clients = args.soak_max_clients
    if args.idle_timeout <= args.interval:
        args.idle_timeout = int(args.interval + 30)
        log(f"raised idle timeout for soak: {args.idle_timeout}s")

    best_effort_hide_menu(args)
    if not args.no_auth:
        get_tcpctl_token(args)
    runner = BridgeRunThread(args, tcpctl_listen_command(args), echo=args.verbose)
    runner.start()

    print("--- ready ---")
    try:
        ready_output = wait_for_tcpctl(args, args.ready_timeout)
    except Exception:
        try:
            tcpctl_request(args, "shutdown", timeout=2.0)
        except Exception:
            pass
        runner.join(args.bridge_timeout)
        raise
    print(ready_output, end="" if ready_output.endswith("\n") else "\n")

    start = time.monotonic()
    next_tick = start
    cycle = 0
    tcp_pass = 0
    status_pass = 0
    run_pass = 0
    ping_pass = 0
    failures: list[str] = []

    try:
        while time.monotonic() - start < args.duration:
            cycle += 1
            elapsed = time.monotonic() - start
            print(f"--- cycle {cycle} elapsed={elapsed:.1f}s ---", flush=True)

            try:
                tcpctl_expect_ok(args, "ping")
                tcp_pass += 1
                print("tcp ping: PASS", flush=True)
            except Exception as exc:
                failures.append(f"cycle {cycle} tcp ping: {exc}")
                print(f"tcp ping: FAIL {exc}", flush=True)

            if args.status_every > 0 and cycle % args.status_every == 0:
                try:
                    status_output = tcpctl_expect_ok(args, "status")
                    status_pass += 1
                    summary = " ".join(
                        line for line in status_output.splitlines()
                        if line.startswith(("uptime:", "load:", "mem:"))
                    )
                    print(f"status: PASS {summary}", flush=True)
                except Exception as exc:
                    failures.append(f"cycle {cycle} status: {exc}")
                    print(f"status: FAIL {exc}", flush=True)

            if args.run_every > 0 and cycle % args.run_every == 0:
                try:
                    tcpctl_expect_ok(args, f"run {args.toybox} uptime")
                    run_pass += 1
                    print("run uptime: PASS", flush=True)
                except Exception as exc:
                    failures.append(f"cycle {cycle} run uptime: {exc}")
                    print(f"run uptime: FAIL {exc}", flush=True)

            if args.ping_every > 0 and cycle % args.ping_every == 0:
                try:
                    host_ping(args, args.ping_count)
                    ping_pass += 1
                    print(f"host ping x{args.ping_count}: PASS", flush=True)
                except Exception as exc:
                    failures.append(f"cycle {cycle} host ping: {exc}")
                    print(f"host ping: FAIL {exc}", flush=True)

            if failures and args.stop_on_failure:
                break

            next_tick += args.interval
            sleep_sec = next_tick - time.monotonic()
            if sleep_sec > 0:
                time.sleep(sleep_sec)
    finally:
        print("--- shutdown ---")
        try:
            shutdown_output = tcpctl_expect_ok(args, "shutdown")
            print(shutdown_output, end="" if shutdown_output.endswith("\n") else "\n")
        except Exception as exc:
            failures.append(f"shutdown: {exc}")
            print(f"shutdown: FAIL {exc}")

        runner.join(args.bridge_timeout)
        if runner.is_alive():
            failures.append("serial run did not finish after shutdown")
        elif runner.error is not None:
            failures.append(f"bridge run failed: {runner.error}")
        elif "[done] run" not in runner.text():
            failures.append("serial run did not report [done] run")

    print("--- serial-run ---")
    print(runner.text(), end="" if runner.text().endswith("\n") else "\n")

    print("--- bridge-version ---")
    try:
        bridge_output = device_command(
            args,
            "version",
            timeout=args.bridge_timeout,
        )
        print(bridge_output, end="" if bridge_output.endswith("\n") else "\n")
    except Exception as exc:
        failures.append(f"bridge version: {exc}")
        print(f"bridge version: FAIL {exc}")

    print("--- final-ncm-ping ---")
    try:
        print(host_ping(args, 3), end="")
    except Exception as exc:
        failures.append(f"final ncm ping: {exc}")
        print(f"final ncm ping: FAIL {exc}")

    elapsed = time.monotonic() - start
    print("--- summary ---")
    print(f"duration: {elapsed:.1f}s")
    print(f"cycles: {cycle}")
    print(f"tcp ping pass: {tcp_pass}")
    print(f"status pass: {status_pass}")
    print(f"run pass: {run_pass}")
    print(f"host ping pass: {ping_pass}")
    print(f"failures: {len(failures)}")

    if failures:
        for failure in failures:
            print(f"- {failure}")
        raise RuntimeError("soak validation failed")

    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--tcp-port", type=int, default=DEFAULT_TCP_PORT)
    parser.add_argument("--device-binary", default=DEFAULT_DEVICE_BINARY)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--idle-timeout", type=int, default=DEFAULT_IDLE_TIMEOUT)
    parser.add_argument("--max-clients", type=int, default=DEFAULT_MAX_CLIENTS)
    parser.add_argument("--token", help="tcpctl auth token; defaults to reading it from native init")
    parser.add_argument("--token-command", default=DEFAULT_TOKEN_COMMAND)
    parser.add_argument("--token-path", default=DEFAULT_TCPCTL_TOKEN_PATH)
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="use legacy unauthenticated tcpctl listen/request mode",
    )
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--tcp-timeout", type=float, default=10.0)
    parser.add_argument("--bridge-timeout", type=float, default=30.0)
    parser.add_argument(
        "--device-protocol",
        choices=("auto", "cmdv1", "raw"),
        default="auto",
        help="device shell command protocol for one-shot bridge checks",
    )
    parser.add_argument("--busy-retries", type=int, default=3)
    parser.add_argument("--busy-retry-sleep", type=float, default=3.0)
    parser.add_argument("--menu-hide-sleep", type=float, default=3.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Host helper for the A90 native-init NCM tcpctl service."
    )
    add_common_args(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="start tcpctl through the serial bridge and stream logs")
    start.set_defaults(func=command_start)

    call = subparsers.add_parser("call", help="send one raw tcpctl command line")
    call.add_argument("line", nargs=argparse.REMAINDER)
    call.set_defaults(func=command_call)

    subparsers.add_parser("ping", help="send ping").set_defaults(func=command_ping)
    subparsers.add_parser("version", help="send version").set_defaults(func=command_version)
    subparsers.add_parser("status", help="send status").set_defaults(func=command_status)
    subparsers.add_parser("stop", help="send shutdown").set_defaults(func=command_stop)

    run = subparsers.add_parser("run", help="run an absolute-path command through tcpctl")
    run.add_argument("run_args", nargs=argparse.REMAINDER)
    run.set_defaults(func=command_run)

    install = subparsers.add_parser("install", help="install a90_tcpctl to /cache/bin over NCM")
    install.add_argument("--local-binary", default=str(DEFAULT_LOCAL_BINARY))
    install.add_argument("--transfer-port", type=int, default=DEFAULT_TRANSFER_PORT)
    install.add_argument("--transfer-delay", type=float, default=2.0)
    install.add_argument("--transfer-timeout", type=float, default=90.0)
    install.add_argument("--install-control-channel", choices=("bridge", "tcpctl"), default="bridge")
    install.add_argument("--verbose", action="store_true")
    install.set_defaults(func=command_install)

    smoke = subparsers.add_parser("smoke", help="start tcpctl, run checks, stop it")
    smoke.add_argument("--install-first", action="store_true")
    smoke.add_argument("--local-binary", default=str(DEFAULT_LOCAL_BINARY))
    smoke.add_argument("--transfer-port", type=int, default=DEFAULT_TRANSFER_PORT)
    smoke.add_argument("--transfer-delay", type=float, default=2.0)
    smoke.add_argument("--transfer-timeout", type=float, default=90.0)
    smoke.add_argument("--ready-timeout", type=float, default=15.0)
    smoke.add_argument("--verbose", action="store_true")
    smoke.set_defaults(func=command_smoke)

    soak = subparsers.add_parser("soak", help="start tcpctl and run a timed NCM/TCP stability loop")
    soak.add_argument("--install-first", action="store_true")
    soak.add_argument("--local-binary", default=str(DEFAULT_LOCAL_BINARY))
    soak.add_argument("--transfer-port", type=int, default=DEFAULT_TRANSFER_PORT)
    soak.add_argument("--transfer-delay", type=float, default=2.0)
    soak.add_argument("--transfer-timeout", type=float, default=90.0)
    soak.add_argument("--ready-timeout", type=float, default=15.0)
    soak.add_argument("--duration", type=float, default=300.0)
    soak.add_argument("--interval", type=float, default=10.0)
    soak.add_argument("--status-every", type=int, default=6)
    soak.add_argument("--run-every", type=int, default=6)
    soak.add_argument("--ping-every", type=int, default=1)
    soak.add_argument("--ping-count", type=int, default=1)
    soak.add_argument("--soak-max-clients", type=int, default=DEFAULT_SOAK_MAX_CLIENTS)
    soak.add_argument("--stop-on-failure", action="store_true")
    soak.add_argument("--verbose", action="store_true")
    soak.set_defaults(func=command_soak)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
