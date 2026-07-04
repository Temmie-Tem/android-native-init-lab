#!/usr/bin/env python3
"""Run WSTA42: D-public quick Tunnel over native-owned STA uplink.

This live gate keeps native init as the Wi-Fi owner, mounts the Debian rootfs as
a chroot service surface, uses the existing native uplink-service confirmed
autoconnect path, then starts the D-public loopback smoke service and
``cloudflared`` from Debian userspace.  It is fail-closed and requires explicit
credentialed Wi-Fi and public-exposure acknowledgements.

Raw Wi-Fi credentials, confirm tokens, private network identifiers, and the
generated public URL are not printed.  The URL is written only to the private
run directory for the host-side smoke request.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import ipaddress
import json
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = SCRIPT_DIR.parent / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import prepare_dpublic_preflight as dpublic  # noqa: E402
import run_d1_chroot_mvp as d1  # noqa: E402
import run_d2_ssh_in_chroot as d2  # noqa: E402
import run_wsta19_native_owned_chroot_wifi as wsta19  # noqa: E402
import run_wsta20_native_wifi_service_boundary as wsta20  # noqa: E402
import run_wsta24_native_wifi_uplink_client as wsta24  # noqa: E402
import run_wsta25_confirmed_autoconnect_live as wsta25  # noqa: E402
import run_wsta2_native_materialization as wsta2  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE
PUBLIC_CONFIRM_TOKEN = dpublic.DPUBLIC_LIVE_OPERATOR_TOKEN
PASS_DECISION = "wsta42-native-uplink-dpublic-tunnel-pass"
SMOKE_SOURCE = SCRIPT_DIR / "a90_dpublic_smoke_httpd.c"
HTTP_GET_SOURCE = SCRIPT_DIR / "a90_dpublic_http_get.c"
REMOTE_CLOUDFLARED = "/usr/local/bin/cloudflared"
REMOTE_SMOKE = "/usr/local/bin/a90-dpublic-smoke-httpd"
REMOTE_HTTP_GET = "/usr/local/bin/a90-dpublic-http-get"
REMOTE_RUN_DIR = "/run/a90-dpublic"
REMOTE_URL_FILE = REMOTE_RUN_DIR + "/cloudflared-live.url"
REMOTE_CLOUDFLARED_LOG = REMOTE_RUN_DIR + "/cloudflared-live.log"
REMOTE_CLOUDFLARED_PID = REMOTE_RUN_DIR + "/cloudflared-live.pid"
REMOTE_SMOKE_PID = REMOTE_RUN_DIR + "/smoke.pid"
REMOTE_SMOKE_LOG = REMOTE_RUN_DIR + "/smoke.log"
DEFAULT_HOST_RESOLVER_CANDIDATES = (
    Path("/run/systemd/resolve/resolv.conf"),
    Path("/etc/resolv.conf"),
)


def rel(path: Path) -> str:
    return wsta2.rel(path)


def write_json(path: Path, payload: Any) -> None:
    d1.write_json(path, payload)


def sha256_file(path: Path) -> str:
    return d1.sha256_file(path)


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.allow_public_live:
        return False, "wsta42-blocked-explicit-public-live-allow-required"
    if not args.ack_credentialed_wifi:
        return False, "wsta42-blocked-credentialed-wifi-ack-required"
    if not args.ack_public_exposure:
        return False, "wsta42-blocked-public-exposure-ack-required"
    if args.native_confirm_token != wsta25.NATIVE_CONFIRM_TOKEN:
        return False, "wsta42-blocked-native-confirm-token-required"
    if args.public_confirm_token != PUBLIC_CONFIRM_TOKEN:
        return False, "wsta42-blocked-public-confirm-token-required"
    return True, "ok"


def run_host(command: list[str], *, timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def build_helper(source: Path, output: Path) -> dict[str, Any]:
    command = [
        "aarch64-linux-gnu-gcc",
        "-O2",
        "-Wall",
        "-Wextra",
        "-static",
        "-o",
        str(output),
        str(source),
    ]
    record = run_host(command, timeout=60.0)
    record["source"] = rel(source)
    record["output"] = rel(output)
    if record["returncode"] == 0:
        output.chmod(0o755)
        record["sha256"] = sha256_file(output)
        record["size_bytes"] = output.stat().st_size
    return record


def build_dpublic_helpers(run_dir: Path) -> dict[str, Any]:
    smoke = run_dir / "a90-dpublic-smoke-httpd"
    http_get = run_dir / "a90-dpublic-http-get"
    result = {
        "smoke_httpd": build_helper(SMOKE_SOURCE, smoke),
        "http_get": build_helper(HTTP_GET_SOURCE, http_get),
    }
    result["ok"] = (
        result["smoke_httpd"].get("returncode") == 0
        and result["http_get"].get("returncode") == 0
    )
    return result


def ssh_command(args: argparse.Namespace, run_dir: Path) -> list[str]:
    key_path = run_dir / "d2_ssh_key_ed25519"
    known_hosts = run_dir / "d2_known_hosts"
    return [
        "ssh",
        "-i",
        str(key_path),
        "-p",
        str(args.ssh_port),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        f"UserKnownHostsFile={known_hosts}",
        "-o",
        f"ConnectTimeout={args.ssh_connect_timeout}",
        "-o",
        "PreferredAuthentications=publickey",
        f"root@{args.device_ip}",
    ]


def ssh_exec(args: argparse.Namespace, run_dir: Path, remote_command: str, *, timeout: float) -> dict[str, Any]:
    command = [*ssh_command(args, run_dir), remote_command]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def ssh_write_file(args: argparse.Namespace,
                   run_dir: Path,
                   local_path: Path,
                   remote_path: str,
                   *,
                   timeout: float) -> dict[str, Any]:
    command = [
        *ssh_command(args, run_dir),
        (
            "set -eu; "
            f"/bin/mkdir -p {shlex.quote(str(Path(remote_path).parent))}; "
            f"/bin/cat > {shlex.quote(remote_path)}; "
            f"/bin/chmod 755 {shlex.quote(remote_path)}; "
            f"/usr/bin/test -x {shlex.quote(remote_path)}; "
            "echo A90WSTA42_FILE_STAGED"
        ),
    ]
    data = local_path.read_bytes()
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    return {
        "command": command,
        "input_bytes": len(data),
        "input_sha256": sha256_file(local_path),
        "input_redacted": False,
        "returncode": completed.returncode,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stdout": stdout,
        "stderr": stderr,
        "staged": completed.returncode == 0 and "A90WSTA42_FILE_STAGED" in stdout,
        "remote_path": remote_path,
    }


def stage_dpublic_binaries(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    return {
        "cloudflared": ssh_write_file(
            args,
            run_dir,
            args.cloudflared,
            REMOTE_CLOUDFLARED,
            timeout=args.cloudflared_stage_timeout,
        ),
        "smoke_httpd": ssh_write_file(
            args,
            run_dir,
            run_dir / "a90-dpublic-smoke-httpd",
            REMOTE_SMOKE,
            timeout=args.ssh_timeout,
        ),
        "http_get": ssh_write_file(
            args,
            run_dir,
            run_dir / "a90-dpublic-http-get",
            REMOTE_HTTP_GET,
            timeout=args.ssh_timeout,
        ),
    }


def stage_binaries_ok(record: dict[str, Any]) -> bool:
    return all(record.get(key, {}).get("staged") for key in ("cloudflared", "smoke_httpd", "http_get"))


def sync_time(args: argparse.Namespace) -> dict[str, Any]:
    epoch = int(time.time())
    return wsta19.try_cmdv1_retry(
        args,
        ["run", "/bin/busybox", "date", "-u", "-s", f"@{epoch}"],
        timeout=args.timeout,
        attempts=1,
    )


def host_resolver_candidates(args: argparse.Namespace) -> list[Path]:
    candidates: list[Path] = []
    for path in [*(args.host_resolver_conf or []), *DEFAULT_HOST_RESOLVER_CANDIDATES]:
        if path not in candidates:
            candidates.append(path)
    return candidates


def usable_resolver_lines(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines: list[str] = []
    for raw_line in text.splitlines():
        parts = raw_line.split()
        if len(parts) < 2 or parts[0] != "nameserver":
            continue
        value = parts[1]
        try:
            addr = ipaddress.ip_address(value.split("%", 1)[0])
        except ValueError:
            continue
        if addr.is_loopback or addr.is_unspecified or addr.is_link_local:
            continue
        lines.append(f"nameserver {value}\n")
    return lines


def select_host_resolver(args: argparse.Namespace) -> dict[str, Any]:
    checked: list[str] = []
    for path in host_resolver_candidates(args):
        checked.append(str(path))
        lines = usable_resolver_lines(path)
        if lines:
            return {
                "path": str(path),
                "checked_count": len(checked),
                "nameserver_count": len(lines),
                "content": "".join(lines),
                "content_redacted": True,
            }
    return {
        "path": "-",
        "checked_count": len(checked),
        "nameserver_count": 0,
        "content": "",
        "content_redacted": True,
    }


def stage_host_resolver(args: argparse.Namespace,
                        run_dir: Path,
                        resolver: dict[str, Any]) -> dict[str, Any]:
    content = str(resolver.get("content") or "")
    command = [
        *ssh_command(args, run_dir),
        (
            "set -eu; "
            "/bin/cat > /etc/resolv.conf; "
            "/bin/chmod 644 /etc/resolv.conf; "
            "COUNT=$(/bin/grep -c '^nameserver ' /etc/resolv.conf 2>/dev/null || true); "
            "echo A90WSTA42_HOST_RESOLVER_STAGED nameserver_count=$COUNT"
        ),
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        input=content.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=args.ssh_timeout,
        check=False,
    )
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    match = re.search(r"A90WSTA42_HOST_RESOLVER_STAGED nameserver_count=([0-9]+)", stdout)
    count = int(match.group(1)) if match else 0
    return {
        "command": command,
        "returncode": completed.returncode,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stdout": stdout,
        "stderr": stderr,
        "input_redacted": True,
        "source_path": resolver.get("path", "-"),
        "source_checked_count": resolver.get("checked_count", 0),
        "source_nameserver_count": resolver.get("nameserver_count", 0),
        "nameserver_count": count,
        "staged": completed.returncode == 0 and count > 0,
    }


def ensure_resolver(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    script = f"""
	set -eu
	MNT={shlex.quote(args.mountpoint)}
	SRC=/cache/a90-wifi/resolv.conf
	DST="$MNT/etc/resolv.conf"
	COUNT=0
	COPIED=0
	READY=0
	SOURCE=missing
	if [ -s "$SRC" ]; then
	  COUNT=$(/bin/busybox grep -c '^nameserver ' "$SRC" || true)
	  /bin/busybox cp "$SRC" "$DST"
	  /bin/busybox chmod 644 "$DST"
	  COPIED=1
	  SOURCE=native-dhcp
	  if [ "$COUNT" -gt 0 ]; then READY=1; fi
	elif [ -s "$DST" ]; then
	  COUNT=$(/bin/busybox grep -c '^nameserver ' "$DST" || true)
	  SOURCE=chroot-existing
	  if [ "$COUNT" -gt 0 ]; then
	    /bin/busybox chmod 644 "$DST"
	    READY=1
	  fi
	else
	  SOURCE=missing
	fi
	echo A90WSTA42_RESOLVER_SYNC ready=$READY copied=$COPIED source=$SOURCE nameserver_count=$COUNT
	""".strip()
    record = wsta19.bridge_shell(args, script, timeout=args.timeout, allow_error=True)
    text = str(record.get("text") or "")
    record["copied"] = "copied=1" in text
    record["ready"] = "ready=1" in text
    source_match = re.search(r"source=([A-Za-z0-9_.:-]+)", text)
    record["source"] = source_match.group(1) if source_match else "-"
    match = re.search(r"nameserver_count=([0-9]+)", text)
    record["nameserver_count"] = int(match.group(1)) if match else 0
    if resolver_ready(record):
        record["host_fallback_attempted"] = False
        return record
    resolver = select_host_resolver(args)
    record["host_fallback_attempted"] = bool(resolver.get("nameserver_count"))
    record["host_fallback_source_path"] = resolver.get("path", "-")
    record["host_fallback_checked_count"] = resolver.get("checked_count", 0)
    record["host_fallback_source_nameserver_count"] = resolver.get("nameserver_count", 0)
    if not resolver.get("nameserver_count"):
        return record
    stage = stage_host_resolver(args, run_dir, resolver)
    record["host_fallback_stage"] = stage
    if stage.get("staged"):
        record["ready"] = True
        record["copied"] = False
        record["source"] = "host-resolver"
        record["nameserver_count"] = int(stage.get("nameserver_count") or 0)
    return record


def resolver_ready(record: dict[str, Any]) -> bool:
    return bool(record.get("ready") and int(record.get("nameserver_count") or 0) > 0)


def native_default_route(args: argparse.Namespace) -> dict[str, Any]:
    script = (
        "/bin/busybox ip route show default 2>/dev/null | "
        "/bin/busybox awk '{for(i=1;i<=NF;i++) if($i==\"dev\") print \"default_route_dev=\"$(i+1)}'"
    )
    record = wsta19.try_cmdv1_retry(
        args,
        ["run", "/bin/busybox", "sh", "-c", script],
        timeout=args.timeout,
        attempts=1,
    )
    text = str(record.get("text") or "")
    match = re.search(r"default_route_dev=([A-Za-z0-9_.:-]+)", text)
    record["default_route_dev"] = match.group(1) if match else "-"
    record["default_route_is_wlan0"] = record["default_route_dev"] == "wlan0"
    return record


def start_smoke(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    command = f"""
	set +e
	/bin/mkdir -p {shlex.quote(REMOTE_RUN_DIR)}
	if [ -s {shlex.quote(REMOTE_SMOKE_PID)} ]; then
	  /bin/kill "$(/bin/cat {shlex.quote(REMOTE_SMOKE_PID)})" 2>/dev/null || true
	fi
	/usr/bin/pkill -f '[a]90-dpublic-smoke-httpd' 2>/dev/null || true
	/bin/rm -f {shlex.quote(REMOTE_SMOKE_PID)} {shlex.quote(REMOTE_SMOKE_LOG)}
	for _ in 1 2 3 4 5; do
	  if /bin/grep -qi ':1F90 .* 0A ' /proc/net/tcp 2>/dev/null; then /bin/sleep 1; else break; fi
	done
	LO_UP_RC=127
	if [ -x /sbin/ip ]; then
	  /sbin/ip link set lo up >/dev/null 2>&1
	  LO_UP_RC=$?
	elif [ -x /usr/sbin/ip ]; then
	  /usr/sbin/ip link set lo up >/dev/null 2>&1
	  LO_UP_RC=$?
	elif [ -x /bin/busybox ]; then
	  /bin/busybox ip link set lo up >/dev/null 2>&1
	  LO_UP_RC=$?
	fi
	echo A90WSTA42_LOOPBACK_UP rc=$LO_UP_RC
	{shlex.quote(REMOTE_SMOKE)} 127.0.0.1 8080 </dev/null >{shlex.quote(REMOTE_SMOKE_LOG)} 2>&1 &
	echo $! > {shlex.quote(REMOTE_SMOKE_PID)}
	/bin/sleep 1
	PID_ALIVE=0
	if /bin/kill -0 "$(/bin/cat {shlex.quote(REMOTE_SMOKE_PID)})" 2>/dev/null; then
	  PID_ALIVE=1
	  echo A90WSTA42_SMOKE_STARTED
	fi
	LISTEN=0
	if /bin/grep -qi ':1F90 .* 0A ' /proc/net/tcp 2>/dev/null; then LISTEN=1; fi
	GET_OUTPUT=$(/usr/bin/timeout 10s {shlex.quote(REMOTE_HTTP_GET)} 127.0.0.1 8080 2>&1)
	GET_RC=$?
	/bin/printf '%s\\n' "$GET_OUTPUT"
	LOG_BYTES=0
	if [ -s {shlex.quote(REMOTE_SMOKE_LOG)} ]; then
	  LOG_BYTES=$(/usr/bin/wc -c < {shlex.quote(REMOTE_SMOKE_LOG)} 2>/dev/null || echo 0)
	fi
	echo A90WSTA42_SMOKE_DIAG pid_alive=$PID_ALIVE listen=$LISTEN http_get_rc=$GET_RC log_bytes=$LOG_BYTES
	if [ -s {shlex.quote(REMOTE_SMOKE_LOG)} ]; then
	  echo A90WSTA42_SMOKE_LOG_BEGIN
	  /usr/bin/tail -n 20 {shlex.quote(REMOTE_SMOKE_LOG)}
	  echo A90WSTA42_SMOKE_LOG_END
	fi
	exit 0
	""".strip()
    record = ssh_exec(args, run_dir, command, timeout=args.ssh_timeout)
    stdout = record.get("stdout", "")
    record["started"] = "A90WSTA42_SMOKE_STARTED" in stdout
    record["local_smoke_ok"] = "A90_DPUBLIC_SMOKE_OK" in stdout
    diag_match = re.search(
        r"A90WSTA42_SMOKE_DIAG pid_alive=([0-9]+) listen=([0-9]+) http_get_rc=([0-9]+) log_bytes=([0-9]+)",
        stdout,
    )
    if diag_match:
        record["pid_alive"] = diag_match.group(1) == "1"
        record["listen"] = diag_match.group(2) == "1"
        record["http_get_rc"] = int(diag_match.group(3))
        record["log_bytes"] = int(diag_match.group(4))
    loopback_match = re.search(r"A90WSTA42_LOOPBACK_UP rc=([0-9]+)", stdout)
    if loopback_match:
        record["loopback_up_rc"] = int(loopback_match.group(1))
    return record


def start_cloudflared(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    command = f"""
set +e
/bin/mkdir -p {shlex.quote(REMOTE_RUN_DIR)}
if [ -s {shlex.quote(REMOTE_CLOUDFLARED_PID)} ]; then
  /bin/kill "$(/bin/cat {shlex.quote(REMOTE_CLOUDFLARED_PID)})" 2>/dev/null || true
fi
	/usr/bin/pkill -f '[c]loudflared tunnel' 2>/dev/null || true
/bin/rm -f {shlex.quote(REMOTE_CLOUDFLARED_PID)} {shlex.quote(REMOTE_CLOUDFLARED_LOG)} {shlex.quote(REMOTE_URL_FILE)}
{shlex.quote(REMOTE_CLOUDFLARED)} tunnel --no-autoupdate --url http://127.0.0.1:8080 --metrics 127.0.0.1:0 --loglevel info </dev/null >{shlex.quote(REMOTE_CLOUDFLARED_LOG)} 2>&1 &
echo $! > {shlex.quote(REMOTE_CLOUDFLARED_PID)}
alive=0
url_observed=0
for _ in $(/usr/bin/seq 1 {int(args.tunnel_url_wait_sec)}); do
  if /bin/kill -0 "$(/bin/cat {shlex.quote(REMOTE_CLOUDFLARED_PID)})" 2>/dev/null; then
    alive=1
  else
    alive=0
    break
  fi
  url=$(/bin/grep -Eo 'https://[A-Za-z0-9-]+\\.trycloudflare\\.com' {shlex.quote(REMOTE_CLOUDFLARED_LOG)} 2>/dev/null | /bin/grep -v '^https://api\\.trycloudflare\\.com$' | /usr/bin/tail -1)
  if [ -n "$url" ]; then
    /usr/bin/printf '%s\\n' "$url" > {shlex.quote(REMOTE_URL_FILE)}
    /bin/chmod 600 {shlex.quote(REMOTE_URL_FILE)}
    url_observed=1
    break
  fi
  /bin/sleep 1
done
echo A90WSTA42_TUNNEL alive=$alive url_observed=$url_observed
""".strip()
    record = ssh_exec(args, run_dir, command, timeout=args.tunnel_url_wait_sec + args.ssh_connect_timeout + 20)
    stdout = record.get("stdout", "")
    record["process_alive"] = "alive=1" in stdout
    record["url_observed"] = "url_observed=1" in stdout
    return record


def fetch_public_url(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    record = ssh_exec(args, run_dir, f"set -eu; /bin/cat {shlex.quote(REMOTE_URL_FILE)}", timeout=args.ssh_timeout)
    url = record.get("stdout", "").strip()
    ok = bool(re.fullmatch(r"https://[A-Za-z0-9-]+\.trycloudflare\.com", url))
    private_path = run_dir / "public-url.txt"
    if ok:
        private_path.write_text(url + "\n", encoding="utf-8")
        private_path.chmod(0o600)
    return {
        "returncode": record.get("returncode"),
        "url_observed": ok,
        "url_len": len(url) if ok else 0,
        "private_path": rel(private_path) if ok else "-",
        "stdout_redacted": True,
        "stderr_present": bool(record.get("stderr", "").strip()),
    }


def host_public_smoke(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    url_path = run_dir / "public-url.txt"
    if not url_path.is_file():
        return {"skipped": True, "reason": "public-url-missing"}
    url = url_path.read_text(encoding="utf-8").strip()
    attempts: list[dict[str, Any]] = []
    started = time.monotonic()
    for attempt in range(1, args.public_smoke_attempts + 1):
        attempt_started = time.monotonic()
        try:
            with urllib.request.urlopen(url, timeout=args.public_curl_timeout_sec) as response:
                body = response.read(4096)
                status = getattr(response, "status", None)
        except urllib.error.HTTPError as exc:
            attempts.append({
                "attempt": attempt,
                "returncode": 1,
                "error_class": type(exc).__name__,
                "http_status": getattr(exc, "code", None),
                "elapsed_sec": round(time.monotonic() - attempt_started, 3),
                "url_redacted": True,
            })
        except Exception as exc:  # noqa: BLE001
            reason = getattr(exc, "reason", None)
            attempts.append({
                "attempt": attempt,
                "returncode": 1,
                "error_class": type(exc).__name__,
                "error_reason_class": type(reason).__name__ if reason is not None else "-",
                "error_errno": getattr(reason, "errno", None),
                "elapsed_sec": round(time.monotonic() - attempt_started, 3),
                "url_redacted": True,
            })
        else:
            body_path = run_dir / "public-curl-body.txt"
            body_path.write_bytes(body)
            result = {
                "returncode": 0,
                "http_status": status,
                "attempt": attempt,
                "attempts": attempts,
                "attempt_count": attempt,
                "elapsed_sec": round(time.monotonic() - started, 3),
                "body_len": len(body),
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "marker_ok": b"A90_DPUBLIC_SMOKE_OK" in body,
                "service_ok": b"service=loopback-http" in body,
                "public_exposure_marker_ok": b"public_exposure=outbound-tunnel-only" in body,
                "url_redacted": True,
                "body_private_path": rel(body_path),
            }
            if result["marker_ok"] and result["service_ok"] and result["public_exposure_marker_ok"]:
                return result
            attempts.append({
                "attempt": attempt,
                "returncode": 1,
                "http_status": status,
                "body_len": len(body),
                "marker_ok": result["marker_ok"],
                "service_ok": result["service_ok"],
                "public_exposure_marker_ok": result["public_exposure_marker_ok"],
                "elapsed_sec": round(time.monotonic() - attempt_started, 3),
                "url_redacted": True,
            })
        if attempt < args.public_smoke_attempts:
            time.sleep(args.public_smoke_retry_delay_sec)
    return {
        "returncode": 1,
        "attempt_count": len(attempts),
        "attempts": attempts,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "url_redacted": True,
    }


def cleanup_dpublic(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    command = f"""
set +e
if [ -s {shlex.quote(REMOTE_CLOUDFLARED_PID)} ]; then
  /bin/kill "$(/bin/cat {shlex.quote(REMOTE_CLOUDFLARED_PID)})" 2>/dev/null || true
fi
if [ -s {shlex.quote(REMOTE_SMOKE_PID)} ]; then
  /bin/kill "$(/bin/cat {shlex.quote(REMOTE_SMOKE_PID)})" 2>/dev/null || true
fi
	/usr/bin/pkill -f '[c]loudflared tunnel' 2>/dev/null || true
	/usr/bin/pkill -f '[a]90-dpublic-smoke-httpd' 2>/dev/null || true
	/bin/rm -f {shlex.quote(REMOTE_CLOUDFLARED_PID)} {shlex.quote(REMOTE_SMOKE_PID)} {shlex.quote(REMOTE_URL_FILE)}
	if /usr/bin/pgrep -f '[c]loudflared tunnel' >/dev/null 2>&1; then echo cloudflared_absent=0; else echo cloudflared_absent=1; fi
	if /usr/bin/pgrep -f '[a]90-dpublic-smoke-httpd' >/dev/null 2>&1; then echo smoke_absent=0; else echo smoke_absent=1; fi
echo A90WSTA42_DPUBLIC_CLEANUP_DONE
""".strip()
    record = ssh_exec(args, run_dir, command, timeout=args.cleanup_timeout)
    stdout = record.get("stdout", "")
    record["cleaned"] = (
        record.get("returncode") == 0
        and "A90WSTA42_DPUBLIC_CLEANUP_DONE" in stdout
        and "cloudflared_absent=1" in stdout
        and "smoke_absent=1" in stdout
    )
    return record


def helper_confirmed_ok(record: dict[str, Any]) -> bool:
    return wsta25.helper_confirmed_ok(record.get("parsed", {}))


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    if not checks.get("explicit_live_gate"):
        return result.get("gate_decision", "wsta42-blocked-explicit-live-gate")
    if not checks.get("native_supported"):
        return "wsta42-blocked-supported-native-not-resident"
    if not checks.get("baseline_selftest_fail_zero") or not checks.get("final_selftest_fail_zero"):
        return "wsta42-blocked-native-health"
    if not checks.get("helpers_built"):
        return "wsta42-blocked-helper-build"
    if not checks.get("debian_ssh_marker"):
        return "wsta42-blocked-debian-chroot-ssh"
    if not checks.get("dpublic_binaries_staged"):
        return "wsta42-blocked-dpublic-binary-stage"
    if not checks.get("native_uplink_confirmed"):
        return "wsta42-blocked-native-uplink-confirmed"
    if not checks.get("default_route_wlan0"):
        return "wsta42-blocked-default-route-not-wlan0"
    if not checks.get("resolver_ready"):
        return "wsta42-blocked-resolver-sync"
    if not checks.get("local_smoke_ok"):
        return "wsta42-blocked-local-smoke"
    if not checks.get("tunnel_url_observed"):
        return "wsta42-blocked-tunnel-url"
    if not checks.get("public_smoke_ok"):
        return "wsta42-blocked-public-smoke"
    if not checks.get("dpublic_cleanup_ok"):
        return "wsta42-blocked-dpublic-cleanup"
    if not checks.get("chroot_cleanup_ok"):
        return "wsta42-blocked-chroot-cleanup"
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"wsta42-native-uplink-dpublic-tunnel-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta42_result.json"

    gate_ok, gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA42 native-owned STA uplink plus Debian D-public quick Tunnel",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "gate_decision": gate_decision,
        "resident_required": {"supported": wsta24.SUPPORTED_UPLINK_NATIVE_BUILDS},
        "remote_image": args.remote_image,
        "mountpoint": args.mountpoint,
        "service_dir": args.service_dir,
        "service_dir_native": args.mountpoint.rstrip("/") + "/" + args.service_dir.lstrip("/"),
        "safety": {
            "boot_flash": False,
            "switch_root": False,
            "userdata_touch": False,
            "wifi_connect": "native-confirm-gated",
            "dhcp_routing": "native-config-gated-after-confirmed-live",
            "public_tunnel": "explicit-public-live-gated",
            "external_ping": False,
            "native_confirm_token_value_logged": False,
            "public_confirm_token_value_logged": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
        "checks": {
            "explicit_live_gate": gate_ok,
            "native_confirm_token_supplied": bool(args.native_confirm_token),
            "native_confirm_token_matches": args.native_confirm_token == wsta25.NATIVE_CONFIRM_TOKEN,
            "public_confirm_token_supplied": bool(args.public_confirm_token),
            "public_confirm_token_matches": args.public_confirm_token == PUBLIC_CONFIRM_TOKEN,
        },
    }
    write_json(out_path, result)
    if not gate_ok:
        result["decision"] = gate_decision
        write_json(out_path, result)
        return result
    # WSTA25's helper executor is intentionally reused and expects this
    # historical argparse field name.  Keep WSTA42's public API explicit while
    # preserving the shared helper contract.
    args.confirm_token = args.native_confirm_token

    local_sha = sha256_file(args.local_image)
    result["local_image"] = rel(args.local_image)
    result["local_image_sha256"] = local_sha
    result["local_image_expected_sha256"] = d1.EXPECTED_IMAGE_SHA256
    result["cloudflared"] = dpublic.verify_cloudflared(
        args.cloudflared,
        dpublic.EXPECTED_CLOUDFLARED_SHA256,
        dpublic.EXPECTED_CLOUDFLARED_SIZE,
    )
    result["helper_build"] = build_dpublic_helpers(run_dir)
    write_json(out_path, result)
    if local_sha != d1.EXPECTED_IMAGE_SHA256:
        result["decision"] = "wsta42-blocked-local-image-sha"
        write_json(out_path, result)
        return result
    if not result["helper_build"].get("ok"):
        result["decision"] = "wsta42-blocked-helper-build"
        write_json(out_path, result)
        return result

    autoconnect_enabled_by_runner = False
    service_started = False
    mounted = False
    helper_staged = False
    try:
        result["bridge_status"] = wsta2.run_host([sys.executable, str(wsta2.BRIDGE), "status", "--json"], timeout=10.0)
        version = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
        status = wsta19.try_cmdv1_retry(args, ["status"], timeout=args.timeout)
        selftest = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
        contract = wsta19.try_cmdv1_retry(args, ["server-distro", "hardware-contract"], timeout=args.timeout)
        result.update({
            "version": version,
            "status": status,
            "baseline_selftest": selftest,
            "hardware_contract": contract,
        })
        write_json(out_path, result)

        if args.enable_autoconnect:
            command = ["wifi", "autoconnect", "enable"]
            if args.autoconnect_profile:
                command.append(args.autoconnect_profile)
            result["autoconnect_enable"] = wsta19.try_cmdv1_retry(args, command, timeout=args.timeout, attempts=1)
            autoconnect_enabled_by_runner = "wifi-autoconnect-enabled" in result["autoconnect_enable"].get("text", "")
            write_json(out_path, result)

        before_sha, before_record = wsta19.remote_sha(args, args.remote_image)
        result["remote_sha_before"] = before_record
        result["remote_sha_before_value"] = before_sha
        if before_sha != local_sha:
            result["install"] = wsta19.install_image(args, local_sha)
        after_sha, after_record = wsta19.remote_sha(args, args.remote_image)
        result["remote_sha_after"] = after_record
        result["remote_sha_after_value"] = after_sha
        if after_sha != local_sha:
            result["decision"] = "wsta42-blocked-remote-image-sha"
            write_json(out_path, result)
            return result
        write_json(out_path, result)

        result["keygen"] = d2.generate_ssh_key(run_dir, run_id)
        public_key = d2.read_public_key(run_dir)
        write_json(out_path, result)

        mount_record = wsta19.bridge_shell(
            args,
            d2.d2_mount_script(args.remote_image, args.mountpoint, args.ssh_port),
            timeout=args.setup_timeout,
        )
        mounted = True
        result["mount"] = mount_record
        result["mount_parse"] = d2.parse_setup(str(mount_record.get("text") or ""))
        write_json(out_path, result)
        if not all(result["mount_parse"].get(key) for key in ("mount_ready", "mounted")):
            result["decision"] = "wsta42-blocked-chroot-mount"
            return result

        start_record = wsta19.bridge_shell(
            args,
            d2.d2_start_dropbear_script(args.mountpoint, public_key, args.device_ip, args.ssh_port),
            timeout=args.setup_timeout,
        )
        result["dropbear_start"] = start_record
        result["dropbear_parse"] = d2.parse_setup(str(start_record.get("text") or ""))
        write_json(out_path, result)
        if not all(result["dropbear_parse"].get(key) for key in ("started", "authorized_keys", "shadow_temp_key_only")):
            result["decision"] = "wsta42-blocked-dropbear-start"
            return result

        result["ssh"] = wsta19.ssh_chroot_marker(args, run_dir)
        result["ssh_parse"] = result["ssh"].get("marker", {})
        write_json(out_path, result)

        result["dpublic_stage"] = stage_dpublic_binaries(args, run_dir)
        write_json(out_path, result)
        if not stage_binaries_ok(result["dpublic_stage"]):
            result["decision"] = "wsta42-blocked-dpublic-binary-stage"
            return result

        result["helper_stage"] = wsta24.stage_helper(args, run_dir)
        helper_staged = bool(result["helper_stage"].get("staged"))
        write_json(out_path, result)
        if not helper_staged:
            result["decision"] = "wsta42-blocked-native-uplink-helper-stage"
            return result

        result["service_start"] = wsta19.try_cmdv1_retry(
            args,
            [
                "wifi",
                "uplink-service",
                "start",
                result["service_dir_native"],
                str(args.service_lifetime_ms),
                str(args.service_poll_ms),
            ],
            timeout=args.timeout,
            attempts=1,
        )
        service_started = "wifi-uplink-service-start-pass" in result["service_start"].get("text", "")
        write_json(out_path, result)
        if not service_started:
            result["decision"] = "wsta42-blocked-uplink-service-start"
            return result

        result["helper_status"] = wsta24.run_helper(args, run_dir, "status", timeout_sec=args.response_timeout_sec)
        write_json(out_path, result)
        if not wsta25.status_ready_for_confirmed_autoconnect(result["helper_status"].get("parsed", {})):
            result["decision"] = "wsta42-blocked-autoconnect-not-ready"
            return result

        result["helper_confirmed"] = wsta25.run_confirmed_helper(
            args,
            run_dir,
            timeout_sec=args.confirmed_timeout_sec,
        )
        write_json(out_path, result)
        if not helper_confirmed_ok(result["helper_confirmed"]):
            result["decision"] = "wsta42-blocked-native-uplink-confirmed"
            return result

        if args.sync_time:
            result["time_sync"] = sync_time(args)
            write_json(out_path, result)

        result["native_default_route"] = native_default_route(args)
        result["resolver_sync"] = ensure_resolver(args, run_dir)
        result["smoke_start"] = start_smoke(args, run_dir)
        write_json(out_path, result)

        if result["native_default_route"].get("default_route_dev") != "wlan0":
            result["decision"] = "wsta42-blocked-default-route-not-wlan0"
            return result
        if not resolver_ready(result["resolver_sync"]):
            result["decision"] = "wsta42-blocked-resolver-sync"
            return result
        if not (result["smoke_start"].get("started") and result["smoke_start"].get("local_smoke_ok")):
            result["decision"] = "wsta42-blocked-local-smoke"
            return result

        result["cloudflared_start"] = start_cloudflared(args, run_dir)
        write_json(out_path, result)
        if not result["cloudflared_start"].get("url_observed"):
            result["decision"] = "wsta42-blocked-tunnel-url"
            return result

        result["public_url_fetch"] = fetch_public_url(args, run_dir)
        result["host_public_smoke"] = host_public_smoke(args, run_dir)
        write_json(out_path, result)
    finally:
        if mounted:
            try:
                result["dpublic_cleanup"] = cleanup_dpublic(args, run_dir)
            except Exception as exc:  # noqa: BLE001
                result["dpublic_cleanup"] = {"error": str(exc), "cleaned": False}
        else:
            result["dpublic_cleanup"] = {"skipped": True, "reason": "chroot-not-mounted"}

        if service_started:
            result["service_stop"] = wsta19.try_cmdv1_retry(
                args,
                ["wifi", "uplink-service", "stop", result["service_dir_native"]],
                timeout=args.timeout,
                attempts=1,
            )
        else:
            result["service_stop"] = {"skipped": True, "reason": "service-not-started"}

        if helper_staged:
            try:
                result["helper_cleanup"] = wsta24.cleanup_helper(args, run_dir)
            except Exception as exc:  # noqa: BLE001
                result["helper_cleanup"] = {"error": str(exc)}
        else:
            result["helper_cleanup"] = {"skipped": True, "reason": "helper-not-staged"}

        try:
            result["service_dir_cleanup"] = wsta20.cleanup_service_dir(args, run_dir)
        except Exception as exc:  # noqa: BLE001
            result["service_dir_cleanup"] = {"error": str(exc)}

        if mounted:
            result["cleanup"] = wsta19.bridge_shell(
                args,
                d2.d2_cleanup_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["cleanup_parse"] = d2.parse_cleanup(str(result["cleanup"].get("text") or ""))
            result["postcheck"] = wsta19.bridge_shell(
                args,
                d2.d2_postcheck_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["postcheck_parse"] = d2.parse_postcheck(str(result["postcheck"].get("text") or ""))
        else:
            result["cleanup"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["cleanup_parse"] = {}
            result["postcheck"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["postcheck_parse"] = {}

        if autoconnect_enabled_by_runner or args.disable_autoconnect_on_cleanup:
            result["autoconnect_disable"] = wsta19.try_cmdv1_retry(
                args,
                ["wifi", "autoconnect", "disable"],
                timeout=args.timeout,
                attempts=1,
            )
        result["wifi_cleanup"] = wsta19.try_cmdv1_retry(args, ["wifi", "cleanup"], timeout=args.timeout, attempts=1)
        result["final_wifi_status"] = wsta19.try_cmdv1_retry(args, ["wifi", "status"], timeout=args.timeout, attempts=1)
        result["final_version"] = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
        result["final_selftest"] = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
        write_json(out_path, result)

    cleanup = result.get("cleanup_parse", {})
    postcheck = result.get("postcheck_parse", {})
    public = result.get("host_public_smoke", {})
    result["checks"] = {
        **result.get("checks", {}),
        "native_supported": wsta24.native_is_v3387(result.get("version", {}).get("text", "")),
        "baseline_selftest_fail_zero": wsta2.selftest_passed(result.get("baseline_selftest", {}).get("text", "")),
        "hardware_contract_ok": wsta2.contract_passed(result.get("hardware_contract", {}).get("text", "")),
        "helpers_built": bool(result.get("helper_build", {}).get("ok")),
        "debian_ssh_marker": bool(result.get("ssh_parse", {}).get("marker")),
        "debian_stage_marker_present": bool(result.get("ssh_parse", {}).get("stage_marker_present")),
        "dpublic_binaries_staged": stage_binaries_ok(result.get("dpublic_stage", {})),
        "native_uplink_confirmed": helper_confirmed_ok(result.get("helper_confirmed", {})),
        "default_route_wlan0": result.get("native_default_route", {}).get("default_route_dev") == "wlan0",
        "resolver_ready": resolver_ready(result.get("resolver_sync", {})),
        "local_smoke_ok": bool(result.get("smoke_start", {}).get("local_smoke_ok")),
        "tunnel_url_observed": bool(result.get("cloudflared_start", {}).get("url_observed")),
        "public_url_value_logged": False,
        "public_smoke_ok": bool(
            public.get("returncode") == 0
            and public.get("marker_ok")
            and public.get("service_ok")
            and public.get("public_exposure_marker_ok")
        ),
        "dpublic_cleanup_ok": bool(result.get("dpublic_cleanup", {}).get("cleaned")),
        "service_stop_pass": "wifi-uplink-service-stop-pass" in str(result.get("service_stop", {}).get("text", "")),
        "helper_cleanup_ok": bool(result.get("helper_cleanup", {}).get("cleaned")),
        "service_dir_cleanup_ok": "A90WSTA20_SERVICE_DIR_REMOVED" in str(result.get("service_dir_cleanup", {}).get("stdout", "")),
        "chroot_cleanup_ok": bool(
            cleanup.get("done")
            and cleanup.get("shadow_restored")
            and cleanup.get("mount_cleanup_ok")
            and cleanup.get("loop_cleanup_ok")
            and postcheck.get("mount_absent")
            and postcheck.get("loop_node_absent")
            and postcheck.get("dropbear_absent")
        ),
        "final_native_supported": wsta24.native_is_v3387(result.get("final_version", {}).get("text", "")),
        "final_selftest_fail_zero": wsta2.selftest_passed(result.get("final_selftest", {}).get("text", "")),
        "secret_values_logged": 0,
    }
    if not result.get("decision") or result.get("decision", "").startswith("wsta42-blocked-public-smoke"):
        result["decision"] = classify(result)
    elif result.get("decision") not in {
        "wsta42-blocked-local-image-sha",
        "wsta42-blocked-helper-build",
        "wsta42-blocked-remote-image-sha",
        "wsta42-blocked-chroot-mount",
        "wsta42-blocked-dropbear-start",
        "wsta42-blocked-dpublic-binary-stage",
        "wsta42-blocked-native-uplink-helper-stage",
        "wsta42-blocked-uplink-service-start",
        "wsta42-blocked-autoconnect-not-ready",
        "wsta42-blocked-native-uplink-confirmed",
        "wsta42-blocked-default-route-not-wlan0",
        "wsta42-blocked-resolver-sync",
        "wsta42-blocked-local-smoke",
        "wsta42-blocked-tunnel-url",
    }:
        result["decision"] = classify(result)
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default=wsta24.DEFAULT_DEVICE_IP)
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--sha-timeout", type=float, default=180.0)
    parser.add_argument("--setup-timeout", type=float, default=180.0)
    parser.add_argument("--cleanup-timeout", type=float, default=120.0)
    parser.add_argument("--ssh-timeout", type=float, default=45.0)
    parser.add_argument("--ssh-connect-timeout", type=int, default=8)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--local-image", type=Path, default=d1.DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--remote-image", default=d1.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--mountpoint", default=d1.DEFAULT_MOUNTPOINT)
    parser.add_argument("--cloudflared", type=Path, default=dpublic.DEFAULT_CLOUDFLARED)
    parser.add_argument("--cloudflared-stage-timeout", type=float, default=180.0)
    parser.add_argument("--host-resolver-conf", type=Path, action="append", default=[])
    parser.add_argument("--service-dir", default="/tmp/a90-native-wifi-uplink-service")
    parser.add_argument("--service-lifetime-ms", type=int, default=360000)
    parser.add_argument("--service-poll-ms", type=int, default=100)
    parser.add_argument("--response-timeout-sec", type=int, default=30)
    parser.add_argument("--confirmed-timeout-sec", type=int, default=300)
    parser.add_argument("--tunnel-url-wait-sec", type=int, default=60)
    parser.add_argument("--public-curl-timeout-sec", type=float, default=25.0)
    parser.add_argument("--public-smoke-attempts", type=int, default=6)
    parser.add_argument("--public-smoke-retry-delay-sec", type=float, default=2.5)
    parser.add_argument("--allow-public-live", action="store_true")
    parser.add_argument("--ack-credentialed-wifi", action="store_true")
    parser.add_argument("--ack-public-exposure", action="store_true")
    parser.add_argument("--native-confirm-token", default="")
    parser.add_argument("--public-confirm-token", default="")
    parser.add_argument("--enable-autoconnect", action="store_true")
    parser.add_argument("--autoconnect-profile", default="")
    parser.add_argument("--disable-autoconnect-on-cleanup", action="store_true", default=True)
    parser.add_argument("--no-sync-time", dest="sync_time", action="store_false", default=True)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / f"wsta42-native-uplink-dpublic-tunnel-{ts}")
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / "wsta42_result.json"
        if out_path.is_file():
            try:
                result = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                result = {
                    "scope": "WSTA42 native-owned STA uplink plus Debian D-public quick Tunnel",
                    "run_dir": rel(run_dir),
                }
        else:
            result = {
                "scope": "WSTA42 native-owned STA uplink plus Debian D-public quick Tunnel",
                "run_dir": rel(run_dir),
            }
        result["decision"] = "wsta42-runner-error"
        result["error"] = str(exc)
        write_json(run_dir / "wsta42_result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main())
