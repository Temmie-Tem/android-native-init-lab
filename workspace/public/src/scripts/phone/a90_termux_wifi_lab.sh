#!/usr/bin/env bash
set -euo pipefail

cmd="${1:-serve}"
root="${A90_WIFI_LAB_DIR:-$HOME/a90-wifi-lab}"
http_port="${A90_WIFI_HTTP_PORT:-8080}"
upload_port="${A90_WIFI_UPLOAD_PORT:-9001}"
sizes_mib="${A90_WIFI_SIZES_MIB:-1 8 32}"
install_deps="${A90_WIFI_LAB_INSTALL:-1}"
bind_host="${A90_WIFI_BIND_HOST:-0.0.0.0}"
allowed_peer="${A90_WIFI_ALLOWED_PEER:-}"
max_upload_mib="${A90_WIFI_MAX_UPLOAD_MIB:-1024}"
max_upload_clients="${A90_WIFI_MAX_UPLOAD_CLIENTS:-1}"
idle_timeout_sec="${A90_WIFI_IDLE_TIMEOUT_SEC:-10}"
lab_token="${A90_WIFI_LAB_TOKEN:-}"
server_py="$root/a90_wifi_lab_server.py"
python_bin="${PYTHON:-}"

log() {
  printf '[a90-wifi-lab] %s\n' "$*"
}

usage() {
  cat <<'EOF'
Usage:
  a90_termux_wifi_lab.sh [serve|serve-no-install|restart|stop|write-server|clean-uploads|clean-all]

Environment:
  A90_WIFI_LAB_DIR=/path/to/workdir      default: $HOME/a90-wifi-lab
  A90_WIFI_HTTP_PORT=8080                download server port
  A90_WIFI_UPLOAD_PORT=9001              raw TCP upload receiver port
  A90_WIFI_SIZES_MIB="1 8 32"            generated download file sizes
  A90_WIFI_LAB_INSTALL=0                 skip Termux pkg install step
  A90_WIFI_BIND_HOST=0.0.0.0             bind address; use phone Wi-Fi IP to narrow exposure
  A90_WIFI_ALLOWED_PEER=192.168.x.y      optional single A90 source IP allowlist
  A90_WIFI_LAB_TOKEN=<token>             optional token; generated when omitted
  A90_WIFI_MAX_UPLOAD_MIB=1024           per-upload size cap
  A90_WIFI_MAX_UPLOAD_CLIENTS=1          concurrent upload cap
  A90_WIFI_IDLE_TIMEOUT_SEC=10           socket idle timeout

Default `serve` installs minimal Termux packages when possible, writes the
embedded Python server, generates test files, starts:
  - HTTP download server on A90_WIFI_HTTP_PORT
  - raw TCP upload receiver on A90_WIFI_UPLOAD_PORT
EOF
}

ensure_packages() {
  if [ "$install_deps" != "1" ]; then
    log "skip package install: A90_WIFI_LAB_INSTALL=$install_deps"
    return 0
  fi

  if command -v pkg >/dev/null 2>&1; then
    log "install/check Termux packages: python coreutils iproute2"
    pkg update -y
    pkg install -y python coreutils iproute2
  else
    log "pkg not found; assuming python/coreutils are already available"
  fi

  if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock || true
    log "termux wake lock requested"
  else
    log "termux-wake-lock not found; keep screen/battery policy in mind"
  fi
}

write_server() {
  mkdir -p "$root"
  cat >"$server_py" <<'PY'
#!/usr/bin/env python3
import argparse
import datetime as _dt
import hashlib
import http.server
import json
import os
import shutil
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path


SERVER_VERSION = "a90-wifi-lab-20260610-auth-limits-v3"


def log(message: str) -> None:
    print(f"[a90-wifi-lab] {message}", flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_sizes(value: str) -> list[int]:
    sizes: list[int] = []
    for item in value.replace(",", " ").split():
        size = int(item)
        if size <= 0:
            raise ValueError(f"invalid non-positive size: {item}")
        sizes.append(size)
    if not sizes:
        raise ValueError("no sizes requested")
    return sizes


def generate_file(path: Path, size_mib: int) -> None:
    target_size = size_mib * 1024 * 1024
    if path.exists() and path.stat().st_size == target_size:
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as handle:
        remaining = target_size
        while remaining > 0:
            chunk_size = min(1024 * 1024, remaining)
            handle.write(os.urandom(chunk_size))
            remaining -= chunk_size
    tmp.replace(path)


def prepare_downloads(root: Path, sizes_mib: list[int]) -> list[dict[str, object]]:
    download_dir = root / "download"
    download_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    sha_lines: list[str] = []
    for size_mib in sizes_mib:
        name = f"test-{size_mib}MiB.bin"
        path = download_dir / name
        log(f"prepare {name}")
        generate_file(path, size_mib)
        digest = sha256_file(path)
        manifest.append(
            {
                "name": name,
                "size_mib": size_mib,
                "bytes": path.stat().st_size,
                "sha256": digest,
            }
        )
        sha_lines.append(f"{digest}  {name}\n")
    (download_dir / "SHA256SUMS.txt").write_text("".join(sha_lines), encoding="utf-8")
    (download_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def read_upload_entries(upload_dir: Path) -> list[dict[str, object]]:
    path = upload_dir / "UPLOADS.jsonl"
    if not path.exists():
        return []
    entries: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            entries.append({"parse_error": True, "raw": line})
    return entries


def safe_upload_entries(upload_dir: Path):
    try:
        return read_upload_entries(upload_dir), None
    except Exception as exc:
        return [], repr(exc)


class A90WifiLabHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self,
                 *args: object,
                 download_dir: Path,
                 upload_dir: Path,
                 token: str,
                 **kwargs: object) -> None:
        self.download_dir = download_dir
        self.upload_dir = upload_dir
        self.token = token
        super().__init__(*args, directory=str(download_dir), **kwargs)

    def log_message(self, fmt: str, *args: object) -> None:
        log("http " + (fmt % args))

    def write_json(self, payload: object, status: int = 200) -> None:
        body = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def write_text(self, body_text: str, status: int = 200) -> None:
        body = body_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self, parsed: urllib.parse.ParseResult) -> bool:
        if not self.token:
            return True
        query = urllib.parse.parse_qs(parsed.query)
        query_tokens = query.get("token", [])
        header_token = self.headers.get("X-A90-Wifi-Lab-Token", "")
        return header_token == self.token or self.token in query_tokens

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if not self.authorized(parsed):
            self.write_json({"error": "unauthorized", "version": SERVER_VERSION}, status=403)
            return
        if path == "/server-version.txt":
            self.write_text(SERVER_VERSION + "\n")
            return
        if path == "/status.json":
            entries, upload_log_error = safe_upload_entries(self.upload_dir)
            self.write_json(
                {
                    "version": SERVER_VERSION,
                    "server": "a90-wifi-lab",
                    "download_root": str(self.download_dir),
                    "upload_root": str(self.upload_dir),
                    "upload_count": len(entries),
                    "upload_log_error": upload_log_error,
                    "latest_upload": entries[-1] if entries else None,
                }
            )
            return
        if path == "/uploads/UPLOADS.jsonl":
            uploads_path = self.upload_dir / "UPLOADS.jsonl"
            try:
                if uploads_path.exists() and uploads_path.is_file():
                    self.write_text(uploads_path.read_text(encoding="utf-8", errors="replace"))
                else:
                    self.write_text("", status=200)
            except Exception as exc:
                self.write_text(f"upload_log_error={exc!r}\n", status=500)
            return
        if path == "/uploads/latest.json":
            entries, upload_log_error = safe_upload_entries(self.upload_dir)
            if entries:
                payload = dict(entries[-1])
                payload["version"] = SERVER_VERSION
                payload["upload_log_error"] = upload_log_error
            else:
                payload = {
                    "version": SERVER_VERSION,
                    "latest_upload": None,
                    "upload_log_error": upload_log_error,
                }
            self.write_json(payload, status=200)
            return
        if path == "/uploads/index.json":
            entries, upload_log_error = safe_upload_entries(self.upload_dir)
            self.write_json(
                {
                    "version": SERVER_VERSION,
                    "upload_log_error": upload_log_error,
                    "uploads": entries,
                },
                status=200,
            )
            return
        return super().do_GET()


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve_http(root: Path, bind_host: str, port: int, token: str, stop: threading.Event) -> None:
    download_dir = root / "download"
    upload_dir = root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    handler = lambda *args, **kwargs: A90WifiLabHandler(  # noqa: E731
        *args,
        download_dir=download_dir,
        upload_dir=upload_dir,
        token=token,
        **kwargs,
    )
    server = ThreadingHTTPServer((bind_host, port), handler)
    server.timeout = 0.5
    log(f"http server listening on {bind_host}:{port}, root={download_dir}, upload_meta={upload_dir}")
    while not stop.is_set():
        server.handle_request()
    server.server_close()


def recv_auth_prefix(conn: socket.socket, token: str) -> tuple[bool, bytes]:
    if not token:
        return True, b""
    prefix = b""
    token_bytes = token.encode("utf-8")
    while b"\n" not in prefix and len(prefix) <= 4096:
        chunk = conn.recv(256)
        if not chunk:
            return False, b""
        prefix += chunk
    line, separator, rest = prefix.partition(b"\n")
    if not separator:
        return False, b""
    return line.rstrip(b"\r") == token_bytes, rest


def recv_one(conn: socket.socket,
             peer: tuple[str, int],
             upload_dir: Path,
             token: str,
             max_upload_bytes: int,
             idle_timeout: float) -> None:
    started = time.monotonic()
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_peer = peer[0].replace(":", "_").replace(".", "_")
    out_path = upload_dir / f"upload-{stamp}-{safe_peer}-{peer[1]}.bin"
    tmp_path = out_path.with_suffix(".bin.tmp")
    digest = hashlib.sha256()
    total = 0
    conn.settimeout(idle_timeout)
    with conn, tmp_path.open("wb") as handle:
        authorized, buffered = recv_auth_prefix(conn, token)
        if not authorized:
            tmp_path.unlink(missing_ok=True)
            log(f"upload rejected peer={peer[0]} reason=bad-token")
            return
        if buffered:
            handle.write(buffered)
            digest.update(buffered)
            total += len(buffered)
        while True:
            data = conn.recv(1024 * 1024)
            if not data:
                break
            if total + len(data) > max_upload_bytes:
                tmp_path.unlink(missing_ok=True)
                log(f"upload rejected peer={peer[0]} reason=size-limit limit={max_upload_bytes}")
                return
            handle.write(data)
            digest.update(data)
            total += len(data)
    tmp_path.replace(out_path)
    elapsed = max(time.monotonic() - started, 0.000001)
    mib_s = total / 1024 / 1024 / elapsed
    result = {
        "path": str(out_path),
        "peer": f"{peer[0]}:{peer[1]}",
        "bytes": total,
        "elapsed_sec": round(elapsed, 6),
        "mib_per_sec": round(mib_s, 3),
        "sha256": digest.hexdigest(),
    }
    out_path.with_suffix(out_path.suffix + ".sha256").write_text(
        f"{result['sha256']}  {out_path.name}\n",
        encoding="utf-8",
    )
    with (upload_dir / "UPLOADS.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result, sort_keys=True) + "\n")
    log(
        "upload received "
        f"bytes={total} elapsed={elapsed:.3f}s speed={mib_s:.3f}MiB/s "
        f"sha256={result['sha256']} path={out_path}"
    )


def serve_upload(root: Path,
                 bind_host: str,
                 port: int,
                 token: str,
                 allowed_peer: str,
                 max_upload_bytes: int,
                 max_clients: int,
                 idle_timeout: float,
                 stop: threading.Event) -> None:
    upload_dir = root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((bind_host, port))
    listener.listen(8)
    listener.settimeout(0.5)
    slots = threading.BoundedSemaphore(max_clients)
    log(
        "upload receiver listening on "
        f"{bind_host}:{port}, root={upload_dir}, max_upload_bytes={max_upload_bytes}, "
        f"max_clients={max_clients}, allowed_peer={allowed_peer or 'any-token-authenticated'}"
    )
    try:
        while not stop.is_set():
            try:
                conn, peer = listener.accept()
            except socket.timeout:
                continue
            if allowed_peer and peer[0] != allowed_peer:
                log(f"upload rejected peer={peer[0]} reason=source-not-allowed")
                conn.close()
                continue
            if not slots.acquire(blocking=False):
                log(f"upload rejected peer={peer[0]} reason=too-many-clients")
                conn.close()
                continue

            def run_upload() -> None:
                try:
                    recv_one(conn, peer, upload_dir, token, max_upload_bytes, idle_timeout)
                except Exception as exc:
                    log(f"upload failed peer={peer[0]} error={exc!r}")
                    try:
                        conn.close()
                    except OSError:
                        pass
                finally:
                    slots.release()

            threading.Thread(
                target=run_upload,
                daemon=True,
            ).start()
    finally:
        listener.close()


def append_addr(addrs: list[str], value: str) -> None:
    value = value.strip()
    if not value or value.startswith("127."):
        return
    parts = value.split(".")
    if len(parts) != 4:
        return
    try:
        if any(int(part) < 0 or int(part) > 255 for part in parts):
            return
    except ValueError:
        return
    if value not in addrs:
        addrs.append(value)


def addrs_from_udp_route() -> list[str]:
    addrs: list[str] = []
    for target in (("8.8.8.8", 80), ("1.1.1.1", 80)):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(target)
            append_addr(addrs, sock.getsockname()[0])
        except OSError:
            pass
        finally:
            sock.close()
    return addrs


def addrs_from_getprop() -> list[str]:
    if not shutil.which("getprop"):
        return []
    addrs: list[str] = []
    try:
        output = subprocess.check_output(
            ["getprop"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return []
    for line in output.splitlines():
        if ".ipaddress]" not in line and ".ip_address]" not in line:
            continue
        if "dhcp." not in line and "wlan" not in line and "wifi" not in line:
            continue
        if ": [" not in line:
            continue
        value = line.rsplit(": [", 1)[-1].rstrip("]")
        append_addr(addrs, value)
    return addrs


def addrs_from_proc_fib_trie() -> list[str]:
    path = Path("/proc/net/fib_trie")
    try:
        if not path.exists():
            return []
    except OSError:
        return []
    addrs: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    previous = ""
    for line in lines:
        stripped = line.strip()
        if stripped == "/32 host LOCAL":
            candidate = previous.split()[-1] if previous.split() else ""
            if not candidate.startswith(("0.", "127.", "224.", "255.")):
                append_addr(addrs, candidate)
        previous = stripped
    return addrs


def get_ipv4_addrs() -> list[str]:
    addrs: list[str] = []
    for value in addrs_from_udp_route():
        append_addr(addrs, value)
    for value in addrs_from_getprop():
        append_addr(addrs, value)
    for value in addrs_from_proc_fib_trie():
        append_addr(addrs, value)
    if shutil.which("ip"):
        try:
            output = subprocess.check_output(
                ["ip", "-o", "-4", "addr", "show", "scope", "global"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for line in output.splitlines():
                fields = line.split()
                if "inet" in fields:
                    value = fields[fields.index("inet") + 1].split("/", 1)[0]
                    append_addr(addrs, value)
        except Exception:
            pass
    return addrs


def print_instructions(addrs: list[str],
                       http_port: int,
                       upload_port: int,
                       manifest: list[dict[str, object]],
                       token: str) -> None:
    token_query = f"?token={urllib.parse.quote(token)}" if token else ""
    log("ready")
    if addrs:
        log("phone IPv4 candidates: " + ", ".join(addrs))
    else:
        log("phone IPv4 candidates unavailable; check Android Wi-Fi details")
    if token:
        log(f"token: {token}")
    log(f"download manifest: http://<PHONE_IP>:{http_port}/manifest.json{token_query}")
    log(f"sha list:          http://<PHONE_IP>:{http_port}/SHA256SUMS.txt{token_query}")
    log(f"upload receiver:   <PHONE_IP>:{upload_port}")
    first = manifest[-1]["name"] if manifest else "test-32MiB.bin"
    print("", flush=True)
    print("A90 download example:", flush=True)
    print(f"  wget 'http://<PHONE_IP>:{http_port}/{first}{token_query}' -O /cache/a90-wifi/{first}", flush=True)
    print(f"  sha256sum /cache/a90-wifi/{first}", flush=True)
    print("", flush=True)
    print("A90 upload example:", flush=True)
    if token:
        print(f"  (printf '%s\\n' '{token}'; cat /cache/a90-wifi/{first}) | nc <PHONE_IP> {upload_port}", flush=True)
    else:
        print(f"  cat /cache/a90-wifi/{first} | nc <PHONE_IP> {upload_port}", flush=True)
    print("", flush=True)
    print("Stop server: Ctrl-C", flush=True)


def ensure_port_available(bind_host: str, port: int, label: str) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((bind_host, port))
    except OSError as exc:
        log(f"{label} {bind_host}:{port} unavailable: {exc}; stop old server or use another port")
        return False
    finally:
        sock.close()
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--bind-host", required=True)
    parser.add_argument("--http-port", type=int, required=True)
    parser.add_argument("--upload-port", type=int, required=True)
    parser.add_argument("--sizes-mib", required=True)
    parser.add_argument("--token", default="")
    parser.add_argument("--allowed-peer", default="")
    parser.add_argument("--max-upload-bytes", type=int, required=True)
    parser.add_argument("--max-upload-clients", type=int, required=True)
    parser.add_argument("--idle-timeout-sec", type=float, required=True)
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    sizes = parse_sizes(args.sizes_mib)
    if args.max_upload_bytes <= 0 or args.max_upload_clients <= 0 or args.idle_timeout_sec <= 0:
        log("max-upload-bytes, max-upload-clients, and idle-timeout-sec must be positive")
        return 2
    if not ensure_port_available(args.bind_host, args.http_port, "http"):
        return 98
    if not ensure_port_available(args.bind_host, args.upload_port, "upload"):
        return 98
    manifest = prepare_downloads(root, sizes)

    stop = threading.Event()

    def handle_signal(_signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    http_thread = threading.Thread(
        target=serve_http,
        args=(root, args.bind_host, args.http_port, args.token, stop),
        daemon=True,
    )
    upload_thread = threading.Thread(
        target=serve_upload,
        args=(
            root,
            args.bind_host,
            args.upload_port,
            args.token,
            args.allowed_peer,
            args.max_upload_bytes,
            args.max_upload_clients,
            args.idle_timeout_sec,
            stop,
        ),
        daemon=True,
    )
    http_thread.start()
    upload_thread.start()
    time.sleep(0.2)
    print_instructions(get_ipv4_addrs(), args.http_port, args.upload_port, manifest, args.token)

    while not stop.is_set():
        time.sleep(0.5)
    log("stopping")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
  chmod +x "$server_py"
  log "wrote $server_py"
}

find_python() {
  if [ -n "$python_bin" ]; then
    printf '%s\n' "$python_bin"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  log "python not found; install Python first"
  return 1
}

run_server() {
  local py
  local max_upload_bytes
  py="$(find_python)"
  if [ -z "$lab_token" ]; then
    lab_token="$("$py" - <<'PY'
import secrets
print(secrets.token_urlsafe(18))
PY
)"
  fi
  max_upload_bytes=$((max_upload_mib * 1024 * 1024))
  exec "$py" "$server_py" \
    --root "$root" \
    --bind-host "$bind_host" \
    --http-port "$http_port" \
    --upload-port "$upload_port" \
    --sizes-mib "$sizes_mib" \
    --token "$lab_token" \
    --allowed-peer "$allowed_peer" \
    --max-upload-bytes "$max_upload_bytes" \
    --max-upload-clients "$max_upload_clients" \
    --idle-timeout-sec "$idle_timeout_sec"
}

stop_servers() {
  local pattern
  pattern="a90_wifi_lab_server.py"
  if command -v pkill >/dev/null 2>&1; then
    pkill -f "$pattern" >/dev/null 2>&1 || true
    log "requested stop for existing $pattern processes"
    return 0
  fi
  log "pkill not available; stop existing server with Ctrl-C or choose alternate ports"
}

case "$cmd" in
  serve)
    ensure_packages
    write_server
    run_server
    ;;
  serve-no-install)
    install_deps=0
    write_server
    run_server
    ;;
  restart)
    stop_servers
    sleep 1
    ensure_packages
    write_server
    run_server
    ;;
  stop)
    stop_servers
    ;;
  write-server)
    write_server
    ;;
  clean-uploads)
    rm -rf "$root/uploads"
    log "removed $root/uploads"
    ;;
  clean-all)
    rm -rf "$root"
    log "removed $root"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
