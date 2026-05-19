#!/usr/bin/env python3
"""v284 CNSS start-only concurrent side-channel feasibility observer.

The serial ACM bridge is intentionally treated as a single foreground control
path.  This tool therefore uses serial only to run the bounded CNSS start-only
helper, while NCM/tcpctl is used as the concurrent read-only observation path.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path  # noqa: E402
from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402
from tcpctl_host import (  # noqa: E402
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_DEVICE_IP,
    DEFAULT_TCPCTL_TOKEN_PATH,
    DEFAULT_TCP_PORT,
    DEFAULT_TOKEN_COMMAND,
    DEFAULT_TOYBOX,
    get_tcpctl_token,
    host_ping,
    tcpctl_expect_ok,
    tcpctl_request,
    wait_for_tcpctl,
)
import wifi_cnss_start_only_runner as start_runner  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v284-cnss-concurrent-sidechannel")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_HELPER = start_runner.DEFAULT_HELPER
DEFAULT_HELPER_SHA256 = start_runner.DEFAULT_HELPER_SHA256
READINESS_TERMS = ("icnss", "cnss", "wlfw", "wlan", "firmware", "qmi", "qca6390")
HOST_ADDR_RE = re.compile(r"^ncm\.host_addr:\s*([0-9A-Fa-f:]{17})$", re.MULTILINE)


@dataclass
class Capture:
    label: str
    ok: bool
    channel: str
    command: str
    duration_sec: float
    status: str
    rc: int | None
    file: str
    error: str = ""


@dataclass
class SerialRunResult:
    ok: bool
    text: str
    rc: int | None
    status: str
    duration_sec: float
    error: str = ""


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_label(text: str) -> str:
    out = []
    for char in text:
        if char.isalnum() or char in "._+-":
            out.append(char)
        else:
            out.append("-")
    label = "".join(out).strip("-")
    while "--" in label:
        label = label.replace("--", "-")
    return label or "capture"


def serial_capture(args: argparse.Namespace,
                   store: EvidenceStore,
                   label: str,
                   command: list[str],
                   *,
                   timeout: float | None = None,
                   allow_error: bool = False,
                   retry_unsafe: bool = False) -> Capture:
    started = time.monotonic()
    out_file = f"commands/serial-{label}.txt"
    try:
        result = run_cmdv1_command(
            args.host,
            args.port,
            args.timeout if timeout is None else timeout,
            command,
            retry_unsafe=retry_unsafe,
        )
        duration = time.monotonic() - started
        store.write_text(out_file, result.text)
        ok = result.rc == 0 and result.status == "ok"
        return Capture(
            label=label,
            ok=ok or allow_error,
            channel="serial-cmdv1",
            command=" ".join(command),
            duration_sec=duration,
            status=result.status,
            rc=result.rc,
            file=str(store.path(out_file)),
        )
    except Exception as exc:  # noqa: BLE001 - keep failure evidence
        duration = time.monotonic() - started
        store.write_text(out_file, f"{type(exc).__name__}: {exc}\n")
        return Capture(
            label=label,
            ok=allow_error,
            channel="serial-cmdv1",
            command=" ".join(command),
            duration_sec=duration,
            status="exception",
            rc=None,
            file=str(store.path(out_file)),
            error=str(exc),
        )


def host_capture(store: EvidenceStore,
                 label: str,
                 command: list[str],
                 *,
                 timeout: float = 10.0) -> tuple[bool, str]:
    out_file = f"commands/host-{label}.txt"
    try:
        result = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        text = result.stdout
        if result.stderr:
            text += result.stderr
        store.write_text(out_file, text)
        return result.returncode == 0, text
    except Exception as exc:  # noqa: BLE001 - host setup evidence
        text = f"{type(exc).__name__}: {exc}\n"
        store.write_text(out_file, text)
        return False, text


def parse_ncm_host_addr(text: str) -> str | None:
    match = HOST_ADDR_RE.search(text)
    if not match:
        return None
    return match.group(1).lower()


def mac_to_enx(mac: str) -> str:
    return "enx" + mac.replace(":", "").lower()


def nmcli_connection_for_device(device: str) -> str | None:
    result = subprocess.run(
        ["nmcli", "-t", "-f", "DEVICE,CONNECTION", "dev", "status"],
        check=False,
        text=True,
        capture_output=True,
        timeout=5.0,
    )
    if result.returncode != 0:
        return None
    prefix = device + ":"
    for line in result.stdout.splitlines():
        if line.startswith(prefix):
            connection = line[len(prefix):]
            return connection if connection and connection != "--" else None
    return None


def fallback_ncm_interface() -> str | None:
    addr_result = subprocess.run(
        ["ip", "-br", "addr"],
        check=False,
        text=True,
        capture_output=True,
        timeout=5.0,
    )
    route_result = subprocess.run(
        ["ip", "route", "show", "default"],
        check=False,
        text=True,
        capture_output=True,
        timeout=5.0,
    )
    if addr_result.returncode != 0:
        return None
    default_devices = set(re.findall(r"\bdev\s+(\S+)", route_result.stdout))
    candidates: list[str] = []
    for line in addr_result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2 or not parts[0].startswith("enx"):
            continue
        device = parts[0]
        if device in default_devices:
            continue
        ipv4 = [part for part in parts[2:] if re.match(r"\d+\.\d+\.\d+\.\d+/", part)]
        if not ipv4 or any(part.startswith("192.168.7.") for part in ipv4):
            candidates.append(device)
    return candidates[0] if len(candidates) == 1 else None


def configure_host_ncm_nmcli(args: argparse.Namespace,
                             store: EvidenceStore,
                             captures: list[Capture],
                             label: str) -> bool:
    if not args.allow_nmcli_host_setup:
        return False

    status = serial_capture(
        args,
        store,
        f"{label}-usbnet-status",
        ["run", "/cache/bin/a90_usbnet", "status"],
        timeout=args.timeout,
        allow_error=True,
        retry_unsafe=True,
    )
    captures.append(status)
    try:
        status_text = Path(status.file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        status_text = ""
    host_addr = parse_ncm_host_addr(status_text)
    device = mac_to_enx(host_addr) if host_addr else None
    if device is None:
        device = fallback_ncm_interface()
    if device is None:
        store.write_text(f"commands/host-{label}-nmcli.txt", "no candidate NCM interface\n")
        return False

    connection = nmcli_connection_for_device(device)
    if connection is None:
        connection = f"a90-ncm-{device}"
        ok, _ = host_capture(
            store,
            f"{label}-nmcli-add",
            [
                "nmcli", "con", "add",
                "type", "ethernet",
                "ifname", device,
                "con-name", connection,
                "ipv4.method", "manual",
                "ipv4.addresses", f"{args.host_ip}/24",
                "ipv6.method", "disabled",
                "autoconnect", "no",
            ],
        )
        if not ok:
            return False
    ok_mod, _ = host_capture(
        store,
        f"{label}-nmcli-mod",
        [
            "nmcli", "con", "mod", connection,
            "ipv4.method", "manual",
            "ipv4.addresses", f"{args.host_ip}/24",
            "ipv6.method", "disabled",
            "autoconnect", "no",
        ],
    )
    ok_up, _ = host_capture(store, f"{label}-nmcli-up", ["nmcli", "con", "up", connection], timeout=20.0)
    host_capture(store, f"{label}-ip-addr", ["ip", "-br", "addr", "show", "dev", device])
    return ok_mod and ok_up


def tcp_capture(args: argparse.Namespace,
                store: EvidenceStore,
                label: str,
                command: str,
                *,
                timeout: float | None = None,
                expect_ok: bool = False) -> Capture:
    started = time.monotonic()
    out_file = f"commands/tcp-{label}.txt"
    try:
        output = tcpctl_expect_ok(args, command) if expect_ok else tcpctl_request(args, command, timeout=timeout)
        duration = time.monotonic() - started
        store.write_text(out_file, output)
        ok = "\nOK" in output or output.rstrip().endswith("OK")
        return Capture(
            label=label,
            ok=ok,
            channel="ncm-tcpctl",
            command=command,
            duration_sec=duration,
            status="ok" if ok else "error",
            rc=0 if ok else 1,
            file=str(store.path(out_file)),
        )
    except Exception as exc:  # noqa: BLE001 - keep failure evidence
        duration = time.monotonic() - started
        store.write_text(out_file, f"{type(exc).__name__}: {exc}\n")
        return Capture(
            label=label,
            ok=False,
            channel="ncm-tcpctl",
            command=command,
            duration_sec=duration,
            status="exception",
            rc=None,
            file=str(store.path(out_file)),
            error=str(exc),
        )


def serial_start_thread(args: argparse.Namespace,
                        store: EvidenceStore,
                        result_box: dict[str, SerialRunResult]) -> threading.Thread:
    helper_args = argparse.Namespace(
        helper=args.helper,
        helper_sha256=args.helper_sha256,
        max_runtime_sec=args.max_runtime_sec,
        command="run",
        allow_daemon_start=True,
        assume_yes=True,
        i_understand_reboot_only_recovery=True,
    )
    command = ["run", *start_runner.helper_start_argv(helper_args)]

    def run() -> None:
        started = time.monotonic()
        out_file = "commands/serial-cnss-start-only-run.txt"
        try:
            result: ProtocolResult = run_cmdv1_command(
                args.host,
                args.port,
                args.timeout + args.max_runtime_sec + 25.0,
                command,
                retry_unsafe=False,
            )
            duration = time.monotonic() - started
            store.write_text(out_file, result.text)
            result_box["serial"] = SerialRunResult(
                ok=result.rc == 0 and result.status == "ok",
                text=result.text,
                rc=result.rc,
                status=result.status,
                duration_sec=duration,
            )
        except Exception as exc:  # noqa: BLE001 - keep failure evidence
            duration = time.monotonic() - started
            store.write_text(out_file, f"{type(exc).__name__}: {exc}\n")
            result_box["serial"] = SerialRunResult(
                ok=False,
                text="",
                rc=None,
                status="exception",
                duration_sec=duration,
                error=str(exc),
            )

    thread = threading.Thread(target=run, name="cnss-start-only-serial", daemon=True)
    thread.start()
    return thread


def netservice_running(text: str) -> bool:
    return "tcpctl=running" in text


def ensure_tcp_sidechannel(args: argparse.Namespace,
                           store: EvidenceStore,
                           captures: list[Capture]) -> dict[str, Any]:
    info: dict[str, Any] = {
        "initial_tcpctl_ready": False,
        "initial_netservice_running": False,
        "started_netservice": False,
        "tcpctl_ready": False,
        "host_ping_ok": False,
        "runtime_helper_alias_created": False,
    }
    captures.append(serial_capture(args, store, "version", ["version"]))
    status = serial_capture(args, store, "netservice-status-before", ["netservice", "status"], allow_error=True)
    captures.append(status)
    try:
        before_text = Path(status.file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        before_text = ""
    info["initial_netservice_running"] = netservice_running(before_text)

    try:
        ping_text = host_ping(args, 1)
        store.write_text("commands/host-ping-before.txt", ping_text)
        info["host_ping_ok"] = True
    except Exception as exc:  # noqa: BLE001 - host may need manual NCM setup
        store.write_text("commands/host-ping-before.txt", f"{type(exc).__name__}: {exc}\n")

    try:
        ready = wait_for_tcpctl(args, 3.0)
        store.write_text("commands/tcp-ready-before.txt", ready)
        if not args.no_auth:
            get_tcpctl_token(args)
        info["initial_tcpctl_ready"] = True
        info["tcpctl_ready"] = True
        return info
    except Exception as exc:  # noqa: BLE001 - may need netservice start
        store.write_text("commands/tcp-ready-before.txt", f"{type(exc).__name__}: {exc}\n")

    if args.command != "run" or args.no_start_netservice:
        return info

    if "tcpctl=no" in before_text and args.allow_runtime_helper_alias:
        captures.append(
            serial_capture(
                args,
                store,
                "runtime-helper-alias-stat-fallback",
                ["stat", args.tcpctl_helper_fallback],
                allow_error=True,
            )
        )
        captures.append(
            serial_capture(
                args,
                store,
                "runtime-helper-alias-copy",
                ["run", args.toybox, "cp", args.tcpctl_helper_fallback, args.tcpctl_helper_required],
                timeout=args.timeout,
                allow_error=True,
                retry_unsafe=True,
            )
        )
        captures.append(
            serial_capture(
                args,
                store,
                "runtime-helper-alias-chmod",
                ["run", args.toybox, "chmod", "755", args.tcpctl_helper_required],
                timeout=args.timeout,
                allow_error=True,
                retry_unsafe=True,
            )
        )
        alias_status = serial_capture(
            args,
            store,
            "runtime-helper-alias-stat-required",
            ["stat", args.tcpctl_helper_required],
            allow_error=True,
        )
        captures.append(alias_status)
        info["runtime_helper_alias_created"] = alias_status.rc == 0 and alias_status.status == "ok"

    captures.append(
        serial_capture(
            args,
            store,
            "netservice-start",
            ["netservice", "start"],
            timeout=max(args.timeout, 45.0),
            allow_error=True,
            retry_unsafe=False,
        )
    )
    info["started_netservice"] = True
    try:
        ready = wait_for_tcpctl(args, args.netservice_ready_timeout)
        store.write_text("commands/tcp-ready-after-start.txt", ready)
        if not args.no_auth:
            get_tcpctl_token(args)
        info["tcpctl_ready"] = True
    except Exception as exc:  # noqa: BLE001 - keep failure evidence
        store.write_text("commands/tcp-ready-after-start.txt", f"{type(exc).__name__}: {exc}\n")
        if configure_host_ncm_nmcli(args, store, captures, "after-netservice-start"):
            try:
                ready = wait_for_tcpctl(args, args.netservice_ready_timeout)
                store.write_text("commands/tcp-ready-after-host-setup.txt", ready)
                if not args.no_auth:
                    get_tcpctl_token(args)
                info["tcpctl_ready"] = True
            except Exception as retry_exc:  # noqa: BLE001
                store.write_text(
                    "commands/tcp-ready-after-host-setup.txt",
                    f"{type(retry_exc).__name__}: {retry_exc}\n",
                )
    try:
        ping_text = host_ping(args, 1)
        store.write_text("commands/host-ping-after-start.txt", ping_text)
        info["host_ping_ok"] = True
    except Exception as exc:  # noqa: BLE001
        store.write_text("commands/host-ping-after-start.txt", f"{type(exc).__name__}: {exc}\n")
    return info


def stop_started_netservice(args: argparse.Namespace,
                            store: EvidenceStore,
                            captures: list[Capture],
                            sidechannel: dict[str, Any]) -> None:
    if not sidechannel.get("started_netservice") or args.keep_netservice:
        return
    captures.append(
        serial_capture(
            args,
            store,
            "netservice-stop-cleanup",
            ["netservice", "stop"],
            timeout=max(args.timeout, 45.0),
            allow_error=True,
            retry_unsafe=False,
        )
    )
    captures.append(serial_capture(args, store, "netservice-status-after-cleanup", ["netservice", "status"], allow_error=True))
    if sidechannel.get("runtime_helper_alias_created") and not args.keep_runtime_helper_alias:
        captures.append(
            serial_capture(
                args,
                store,
                "runtime-helper-alias-remove",
                ["run", args.toybox, "rm", "-f", args.tcpctl_helper_required],
                timeout=args.timeout,
                allow_error=True,
                retry_unsafe=True,
            )
        )


def sample_sidechannel(args: argparse.Namespace,
                       store: EvidenceStore,
                       serial_thread: threading.Thread) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    start = time.monotonic()
    index = 0
    while serial_thread.is_alive() and time.monotonic() - start <= args.observe_timeout:
        index += 1
        sample_started = time.monotonic()
        sample_dir = f"samples/sample-{index:03d}"
        store.mkdir(sample_dir)
        commands = [
            ("ping", "ping", False),
            ("status", "status", False),
            ("netdev", f"run {args.toybox} cat /proc/net/dev", True),
            ("sys-class-net", f"run {args.toybox} ls /sys/class/net", True),
            ("dmesg", f"run {args.toybox} dmesg", True),
        ]
        captures: list[Capture] = []
        for label, command, expect_ok in commands:
            captures.append(
                tcp_capture(
                    args,
                    store,
                    f"sample-{index:03d}-{label}",
                    command,
                    timeout=args.tcp_timeout,
                    expect_ok=expect_ok,
                )
            )
        samples.append(
            {
                "index": index,
                "started_offset_sec": sample_started - start,
                "duration_sec": time.monotonic() - sample_started,
                "during_serial_run": serial_thread.is_alive(),
                "captures": [asdict(item) for item in captures],
            }
        )
        sleep_for = args.sample_interval - (time.monotonic() - sample_started)
        if sleep_for > 0:
            time.sleep(sleep_for)
    return samples


def readiness_lines_from_file(path: str) -> list[str]:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if lowered.startswith("a90_tcpctl ") or lowered in {"ok", "pong"}:
            continue
        if any(term in lowered for term in READINESS_TERMS):
            lines.append(line.strip())
    return lines[-20:]


def file_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def classify(manifest: dict[str, Any]) -> tuple[bool, str, str]:
    sidechannel = manifest["sidechannel"]
    if manifest["mode"] == "plan":
        return True, "cnss-sidechannel-plan-ready", "documented serial/NCM split without live execution"
    if not sidechannel.get("tcpctl_ready"):
        return False, "cnss-sidechannel-blocked", "NCM/tcpctl side-channel is not ready"
    if not sidechannel.get("host_ping_ok"):
        return False, "cnss-sidechannel-host-ncm-blocked", "host NCM ping did not pass"
    if manifest["mode"] == "preflight":
        return True, "cnss-sidechannel-preflight-ready", "NCM/tcpctl side-channel is reachable; no daemon executed"

    serial = manifest.get("serial_start") or {}
    if not serial.get("ok"):
        return False, "cnss-sidechannel-start-failed", "serial CNSS start-only command failed"
    helper_result = ((serial.get("cnss_start") or {}).get("result")) or "missing"
    if helper_result != "start-only-pass":
        return False, "cnss-sidechannel-start-not-pass", f"helper result is {helper_result}"
    if not manifest["comparison"].get("postflight_process_clean"):
        return False, "cnss-sidechannel-process-leak", "postflight CNSS process table is not clean"
    if not manifest["comparison"].get("during_sample_ok"):
        return False, "cnss-sidechannel-unproven", "no NCM/tcpctl sample completed while serial start-only was active"
    if manifest["comparison"].get("wlan_surface_visible"):
        return False, "cnss-sidechannel-wlan-surface-leak", "wlan/wiphy appeared during bounded start-only"
    if manifest["comparison"].get("readiness_line_count", 0) > 0:
        return True, "cnss-sidechannel-readiness-lines-observed", "concurrent side-channel observed readiness-related text"
    return True, "cnss-sidechannel-no-readiness-delta", "concurrent side-channel worked but no readiness delta appeared"


def serial_start_summary(result: SerialRunResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    keys = start_runner.parse_cnss_start_keys(result.text)
    return {
        "ok": result.ok,
        "rc": result.rc,
        "status": result.status,
        "duration_sec": result.duration_sec,
        "error": result.error,
        "cnss_start": keys,
    }


def build_comparison(manifest: dict[str, Any]) -> dict[str, Any]:
    samples = manifest.get("samples") or []
    during_ok = False
    readiness_lines: list[str] = []
    wlan_visible = False
    for sample in samples:
        captures = sample.get("captures") or []
        sample_ok = any(item.get("ok") for item in captures)
        if sample.get("during_serial_run") and sample_ok:
            during_ok = True
        for item in captures:
            command = item.get("command", "")
            if "dmesg" in command or "cat /proc/net/dev" in command or "ls /sys/class/net" in command:
                readiness_lines.extend(readiness_lines_from_file(str(item.get("file", ""))))
            if "cat /proc/net/dev" in command:
                text = file_text(str(item.get("file", "")))
                if re.search(r"^\s*wlan\S*:", text, re.MULTILINE):
                    wlan_visible = True
            if "ls /sys/class/net" in command:
                text = file_text(str(item.get("file", "")))
                if "wlan" in text.lower() or "wiphy" in text.lower():
                    wlan_visible = True
    postflight = manifest.get("postflight") or {}
    return {
        "during_sample_ok": during_ok,
        "sample_count": len(samples),
        "readiness_line_count": len(readiness_lines),
        "readiness_lines_tail": readiness_lines[-20:],
        "wlan_surface_visible": wlan_visible,
        "postflight_process_clean": bool(postflight.get("clean", True)),
    }


def render_summary(manifest: dict[str, Any]) -> str:
    sample_rows = []
    for sample in manifest.get("samples") or []:
        ok_count = sum(1 for item in sample.get("captures", []) if item.get("ok"))
        sample_rows.append([
            str(sample["index"]),
            "yes" if sample.get("during_serial_run") else "no",
            f"{ok_count}/{len(sample.get('captures', []))}",
            f"{sample.get('duration_sec', 0.0):.3f}s",
        ])
    capture_rows = [
        [item["label"], item["channel"], "PASS" if item["ok"] else "FAIL", item["status"]]
        for item in manifest.get("captures", [])
    ]
    lines = [
        "# CNSS Concurrent Side-Channel Observer\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- mode: `{manifest['mode']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: {manifest['reason']}\n",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`\n",
        f"- sidechannel_ready: `{manifest['sidechannel'].get('tcpctl_ready')}`\n",
        f"- started_netservice: `{manifest['sidechannel'].get('started_netservice')}`\n\n",
        "## Captures\n\n",
        markdown_table(["label", "channel", "result", "status"], capture_rows),
        "\n\n## Concurrent Samples\n\n",
        markdown_table(["sample", "during", "ok", "duration"], sample_rows),
        "\n\n## Comparison\n\n",
        f"- during_sample_ok: `{manifest['comparison'].get('during_sample_ok')}`\n",
        f"- readiness_line_count: `{manifest['comparison'].get('readiness_line_count')}`\n",
        f"- wlan_surface_visible: `{manifest['comparison'].get('wlan_surface_visible')}`\n",
        f"- postflight_process_clean: `{manifest['comparison'].get('postflight_process_clean')}`\n\n",
        "## Guardrails\n\n",
        "- serial ACM is used for exactly one bounded CNSS start-only foreground command.\n",
        "- NCM/tcpctl is used only for read-only observation commands.\n",
        "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing is performed.\n",
        "- no QMI payload, QRTR nameservice packet, rfkill write, ICNSS bind/unbind, or reboot is performed.\n",
    ]
    return "".join(lines)


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    captures: list[Capture] = []
    sidechannel = {
        "initial_tcpctl_ready": False,
        "initial_netservice_running": False,
        "started_netservice": False,
        "tcpctl_ready": False,
        "host_ping_ok": False,
    }
    samples: list[dict[str, Any]] = []
    serial_result: SerialRunResult | None = None
    daemon_start_executed = False
    postflight: dict[str, Any] = {"clean": True}

    if args.command != "plan":
        sidechannel = ensure_tcp_sidechannel(args, store, captures)

    if args.command == "run" and sidechannel.get("tcpctl_ready") and sidechannel.get("host_ping_ok"):
        result_box: dict[str, SerialRunResult] = {}
        thread = serial_start_thread(args, store, result_box)
        daemon_start_executed = True
        time.sleep(args.initial_observe_delay)
        samples = sample_sidechannel(args, store, thread)
        thread.join(args.timeout + args.max_runtime_sec + 25.0)
        serial_result = result_box.get("serial")
        postflight_capture = serial_capture(
            args,
            store,
            "post-cnss-processes",
            ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm"],
            timeout=args.timeout,
            allow_error=True,
            retry_unsafe=True,
        )
        captures.append(postflight_capture)
        try:
            post_text = Path(postflight_capture.file).read_text(encoding="utf-8", errors="replace")
        except OSError:
            post_text = ""
        postflight = {
            "clean": "cnss-daemon" not in post_text and "cnss_diag" not in post_text,
            "capture": asdict(postflight_capture),
        }

    stop_started_netservice(args, store, captures, sidechannel)
    manifest: dict[str, Any] = {
        "created": now_iso(),
        "mode": args.command,
        "host_metadata": collect_host_metadata(),
        "out_dir": str(out_dir),
        "daemon_start_executed": daemon_start_executed,
        "wifi_packet_transmission": False,
        "usb_ncm_control_packets": args.command != "plan",
        "qmi_payload": False,
        "sidechannel": sidechannel,
        "serial_start": serial_start_summary(serial_result),
        "samples": samples,
        "postflight": postflight,
        "captures": [asdict(item) for item in captures],
        "guardrails": [
            "no QMI payload",
            "no QRTR nameservice packet",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill write",
            "no ICNSS bind/unbind",
            "no reboot/recovery/poweroff",
        ],
    }
    manifest["comparison"] = build_comparison(manifest)
    pass_ok, decision, reason = classify(manifest)
    manifest["pass"] = pass_ok
    manifest["decision"] = decision
    manifest["reason"] = reason
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--host-ip", default="192.168.7.1")
    parser.add_argument("--tcp-port", type=int, default=DEFAULT_TCP_PORT)
    parser.add_argument("--tcp-timeout", type=float, default=10.0)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    parser.add_argument("--bridge-timeout", type=float, default=45.0)
    parser.add_argument("--token", help="tcpctl auth token; defaults to native init netservice token")
    parser.add_argument("--token-command", default=DEFAULT_TOKEN_COMMAND)
    parser.add_argument("--token-path", default=DEFAULT_TCPCTL_TOKEN_PATH)
    parser.add_argument("--no-auth", action="store_true")
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--max-runtime-sec", type=int, default=10)
    parser.add_argument("--observe-timeout", type=float, default=20.0)
    parser.add_argument("--sample-interval", type=float, default=1.0)
    parser.add_argument("--initial-observe-delay", type=float, default=0.5)
    parser.add_argument("--netservice-ready-timeout", type=float, default=20.0)
    parser.add_argument("--no-start-netservice", action="store_true")
    parser.add_argument("--keep-netservice", action="store_true")
    parser.add_argument("--allow-runtime-helper-alias", action="store_true")
    parser.add_argument("--keep-runtime-helper-alias", action="store_true")
    parser.add_argument("--allow-nmcli-host-setup", action="store_true")
    parser.add_argument("--tcpctl-helper-required", default="/bin/a90_tcpctl")
    parser.add_argument("--tcpctl-helper-fallback", default="/cache/bin/a90_tcpctl")
    parser.add_argument("--device-protocol", choices=("auto", "cmdv1", "raw"), default="auto")
    parser.add_argument("--busy-retries", type=int, default=3)
    parser.add_argument("--busy-retry-sleep", type=float, default=3.0)
    parser.add_argument("--menu-hide-sleep", type=float, default=3.0)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    run = subparsers.add_parser("run")
    run.add_argument("--allow-daemon-start", action="store_true")
    run.add_argument("--assume-yes", action="store_true")
    run.add_argument("--i-understand-reboot-only-recovery", action="store_true")
    args = parser.parse_args()
    args.bridge_host = args.host
    args.bridge_port = args.port
    if args.max_runtime_sec < 1 or args.max_runtime_sec > 30:
        raise SystemExit("--max-runtime-sec must be 1..30")
    if args.sample_interval <= 0:
        raise SystemExit("--sample-interval must be positive")
    if args.command != "run":
        args.allow_daemon_start = False
        args.assume_yes = False
        args.i_understand_reboot_only_recovery = False
    if args.command == "run" and not (
        args.allow_daemon_start
        and args.assume_yes
        and args.i_understand_reboot_only_recovery
    ):
        raise SystemExit("run requires --allow-daemon-start --assume-yes --i-understand-reboot-only-recovery")
    return args


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {manifest['out_dir']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
