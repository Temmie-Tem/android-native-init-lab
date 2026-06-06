#!/usr/bin/env python3
"""V2111 non-root PTY selftest for serial_tcp_bridge TX queue integrity."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pty
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2111-serial-bridge-txqueue-selftest"
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V2111_SERIAL_BRIDGE_TX_QUEUE_SELFTEST_2026-06-05.md"
PAYLOAD_SIZE = 256 * 1024
TIMEOUT_SEC = 12.0


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def connect_when_ready(port: int, deadline: float) -> socket.socket | None:
    while time.monotonic() < deadline:
        try:
            return socket.create_connection(("127.0.0.1", port), timeout=0.2)
        except OSError:
            time.sleep(0.05)
    return None


def read_exact_or_timeout(master_fd: int, expected_len: int, deadline: float) -> bytes:
    chunks: list[bytes] = []
    total = 0
    os.set_blocking(master_fd, False)
    while time.monotonic() < deadline and total < expected_len:
        try:
            chunk = os.read(master_fd, min(65536, expected_len - total))
        except BlockingIOError:
            time.sleep(0.01)
            continue
        if not chunk:
            time.sleep(0.01)
            continue
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V2111 Serial Bridge TX Queue Selftest",
        "",
        "## Summary",
        "",
        "- Cycle: `V2111`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Matrix",
        "",
        "| area | value | detail |",
        "| --- | --- | --- |",
        f"| bridge_started | {manifest['bridge_started']} | port={manifest['port']} |",
        f"| payload_bytes | {manifest['payload_len']} | received={manifest['received_len']} |",
        f"| sha256_match | {manifest['sha256_match']} | payload={manifest['payload_sha256']} received={manifest['received_sha256']} |",
        f"| stdout | `{manifest['stdout']}` | |",
        f"| stderr | `{manifest['stderr']}` | |",
        f"| capture | `{manifest['capture']}` | |",
        "",
        "## Interpretation",
        "",
        "- This is a host-only pseudo-terminal validation of the V2110 bridge fix.",
        "- It proves the bridge no longer relies on a single nonblocking `os.write()` for client-to-serial bytes in this controlled PTY path.",
        "- It does not prove live `/dev/ttyACM0` access or any WLAN producer behavior.",
        "",
        "## Validation",
        "",
        "- `python3 scripts/revalidation/serial_bridge_tx_queue_selftest_v2111.py`",
        "- `python3 -m py_compile scripts/revalidation/serial_bridge_tx_queue_selftest_v2111.py scripts/revalidation/serial_tcp_bridge.py`",
        "- `git diff --check`",
        "",
        "## Safety",
        "",
        "- No device serial node, flash, reboot, test boot, rollback, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan, bind/unbind, PMIC/GPIO/GDSC/regulator write, or firmware/partition write was used.",
        "",
        "## Next",
        "",
        "- Start the patched bridge against real `/dev/ttyACM0` as root/dialout and rerun V2107.",
        "",
    ])


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)
    os.close(slave_fd)
    port = pick_port()
    stdout_path = OUT_DIR / "bridge.stdout.txt"
    stderr_path = OUT_DIR / "bridge.stderr.txt"
    capture_path = OUT_DIR / "bridge.capture.log"
    payload = (b"V2111-serial-bridge-tx-queue:" + bytes(range(256))) * (
        PAYLOAD_SIZE // (len(b"V2111-serial-bridge-tx-queue:") + 256) + 1
    )
    payload = payload[:PAYLOAD_SIZE]
    bridge_cmd = [
        sys.executable,
        "scripts/revalidation/serial_tcp_bridge.py",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--device",
        slave_name,
        "--capture",
        str(capture_path),
        "--bind-retries",
        "0",
    ]

    with stdout_path.open("wb") as stdout_fp, stderr_path.open("wb") as stderr_fp:
        proc = subprocess.Popen(
            bridge_cmd,
            cwd=REPO_ROOT,
            stdout=stdout_fp,
            stderr=stderr_fp,
        )
        try:
            deadline = time.monotonic() + TIMEOUT_SEC
            client = connect_when_ready(port, deadline)
            bridge_started = client is not None
            received = b""
            if client is not None:
                with client:
                    client.sendall(payload)
                    client.shutdown(socket.SHUT_WR)
                    received = read_exact_or_timeout(master_fd, len(payload), deadline)
            payload_hash = sha256(payload)
            received_hash = sha256(received)
            passed = bridge_started and received == payload
            label = "serial-bridge-tx-queue-pty-pass" if passed else "serial-bridge-tx-queue-pty-fail"
            reason = (
                "PTY bridge received the exact queued payload"
                if passed else
                "PTY bridge did not receive the exact queued payload before timeout"
            )
            manifest: dict[str, Any] = {
                "created": dt.datetime.now(dt.timezone.utc).isoformat(),
                "cycle": "V2111",
                "decision": f"v2111-{label}",
                "label": label,
                "pass": passed,
                "reason": reason,
                "out_dir": rel(OUT_DIR),
                "bridge_cmd": bridge_cmd,
                "bridge_started": bridge_started,
                "port": port,
                "slave": slave_name,
                "payload_len": len(payload),
                "received_len": len(received),
                "payload_sha256": payload_hash,
                "received_sha256": received_hash,
                "sha256_match": payload_hash == received_hash,
                "stdout": rel(stdout_path),
                "stderr": rel(stderr_path),
                "capture": rel(capture_path),
            }
            (OUT_DIR / "manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            report = render_report(manifest)
            (OUT_DIR / "summary.md").write_text(report, encoding="utf-8")
            REPORT_PATH.write_text(report, encoding="utf-8")
            print(f"{'PASS' if passed else 'FAIL'} label={label} out_dir={rel(OUT_DIR)}")
            return 0 if passed else 1
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
            os.close(master_fd)


if __name__ == "__main__":
    raise SystemExit(main())
