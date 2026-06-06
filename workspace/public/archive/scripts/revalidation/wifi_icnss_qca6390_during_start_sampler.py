#!/usr/bin/env python3
"""v285 ICNSS/QCA6390 focused during-start side-channel sampler.

This tool reuses the v284 serial/NCM split.  Serial ACM runs exactly one
bounded CNSS start-only helper command.  NCM/tcpctl concurrently samples
read-only ICNSS/QCA6390/WLAN state while the serial command is active.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402
from tcpctl_host import (  # noqa: E402
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_DEVICE_IP,
    DEFAULT_TCPCTL_TOKEN_PATH,
    DEFAULT_TCP_PORT,
    DEFAULT_TOKEN_COMMAND,
    DEFAULT_TOYBOX,
)
import wifi_cnss_concurrent_sidechannel_observer as side  # noqa: E402
import wifi_cnss_start_only_runner as start_runner  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v285-icnss-qca6390-during-start")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_HELPER = start_runner.DEFAULT_HELPER
DEFAULT_HELPER_SHA256 = start_runner.DEFAULT_HELPER_SHA256

ICNSS_NODE = "/sys/devices/platform/soc/18800000.qcom,icnss"
QCA6390_NODE = "/sys/devices/platform/soc/a0000000.qcom,cnss-qca6390"
WLAN_MODULE = "/sys/module/wlan"
ICNSS_MODULE = "/sys/module/icnss"

FOCUS_RE = re.compile(r"(icnss|cnss|wlfw|qmi|qca6390|wlan|wifi|wiphy|firmware|fw|msa)", re.IGNORECASE)
WLAN_SURFACE_RE = re.compile(r"(^|\s)(wlan\S*|swlan\S*|p2p\S*|wiphy\S*|phy\d+)(\s|:|$)", re.IGNORECASE)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def clean_output(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip().replace("<NULL>", "")
        if not line:
            continue
        if line.startswith("a90_tcpctl "):
            continue
        if line == "OK authenticated":
            continue
        if re.fullmatch(r"\[pid\s+\d+\]", line):
            continue
        if re.fullmatch(r"\[exit\s+-?\d+\]", line):
            continue
        if line in {"OK", "FAIL", "pong"}:
            continue
        lines.append(line)
    return "\n".join(lines)


def focus_lines(text: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for line in clean_output(text).splitlines():
        if not FOCUS_RE.search(line):
            continue
        if line not in seen:
            seen.add(line)
            result.append(line)
    return result


def state_signal(label: str, text: str) -> str:
    cleaned = clean_output(text)
    if label in {"ping", "status"}:
        return ""
    if label in {
        "proc-modules",
        "proc-interrupts",
        "proc-net-dev",
        "sys-class-net",
        "sys-class-ieee80211",
        "sys-class-rfkill",
        "dmesg",
    }:
        return "\n".join(focus_lines(cleaned))
    return cleaned


def text_has_wlan_surface(label: str, text: str) -> bool:
    cleaned = clean_output(text)
    if label in {"sys-class-ieee80211"} and cleaned and "No such file" not in cleaned:
        return True
    if label in {"proc-net-dev", "sys-class-net", "dmesg", "proc-interrupts"}:
        return bool(WLAN_SURFACE_RE.search(cleaned))
    return False


def focused_commands(args: argparse.Namespace) -> list[tuple[str, str, bool]]:
    toybox = args.toybox
    return [
        ("ping", "ping", False),
        ("status", "status", False),
        ("icnss-uevent", f"run {toybox} cat {ICNSS_NODE}/uevent", False),
        ("icnss-modalias", f"run {toybox} cat {ICNSS_NODE}/modalias", False),
        ("icnss-driver-link", f"run {toybox} ls -l {ICNSS_NODE}/driver", False),
        ("qca6390-uevent", f"run {toybox} cat {QCA6390_NODE}/uevent", False),
        ("qca6390-modalias", f"run {toybox} cat {QCA6390_NODE}/modalias", False),
        ("qca6390-driver-link", f"run {toybox} ls -l {QCA6390_NODE}/driver", False),
        ("wlan-fwpath", f"run {toybox} cat {WLAN_MODULE}/parameters/fwpath", False),
        ("wlan-con-mode", f"run {toybox} cat {WLAN_MODULE}/parameters/con_mode", False),
        ("wlan-country-code", f"run {toybox} cat {WLAN_MODULE}/parameters/country_code", False),
        ("icnss-quirks", f"run {toybox} cat {ICNSS_MODULE}/parameters/quirks", False),
        ("icnss-dynamic-feature-mask", f"run {toybox} cat {ICNSS_MODULE}/parameters/dynamic_feature_mask", False),
        ("proc-modules", f"run {toybox} cat /proc/modules", False),
        ("proc-interrupts", f"run {toybox} cat /proc/interrupts", False),
        ("proc-net-dev", f"run {toybox} cat /proc/net/dev", False),
        ("sys-class-net", f"run {toybox} ls /sys/class/net", False),
        ("sys-class-ieee80211", f"run {toybox} ls /sys/class/ieee80211", False),
        ("sys-class-rfkill", f"run {toybox} ls /sys/class/rfkill", False),
        ("dmesg", f"run {toybox} dmesg", False),
    ]


def load_capture_text(capture: side.Capture) -> str:
    try:
        return Path(capture.file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def capture_focused_sample(args: argparse.Namespace,
                           store: EvidenceStore,
                           index: int,
                           phase: str,
                           during_serial_run: bool) -> dict[str, Any]:
    sample_started = time.monotonic()
    sample_dir = f"samples/sample-{index:03d}-{phase}"
    store.mkdir(sample_dir)
    captures: list[side.Capture] = []
    signals: dict[str, dict[str, Any]] = {}
    for label, command, expect_ok in focused_commands(args):
        capture = side.tcp_capture(
            args,
            store,
            f"sample-{index:03d}-{phase}-{label}",
            command,
            timeout=args.tcp_timeout,
            expect_ok=expect_ok,
        )
        captures.append(capture)
        text = load_capture_text(capture)
        signal = state_signal(label, text)
        focused = focus_lines(text)
        signals[label] = {
            "ok": capture.ok,
            "status": capture.status,
            "hash": sha256_text(signal),
            "line_count": len(signal.splitlines()) if signal else 0,
            "focus_line_count": len(focused),
            "focus_tail": focused[-8:],
            "wlan_surface": text_has_wlan_surface(label, text),
        }
    ok_count = sum(1 for item in captures if item.ok)
    return {
        "index": index,
        "phase": phase,
        "started": now_iso(),
        "duration_sec": time.monotonic() - sample_started,
        "during_serial_run": during_serial_run,
        "ok_count": ok_count,
        "capture_count": len(captures),
        "captures": [asdict(item) for item in captures],
        "signals": signals,
    }


def sample_during_run(args: argparse.Namespace,
                      store: EvidenceStore,
                      serial_thread: Any,
                      start_index: int) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    started = time.monotonic()
    index = start_index
    while serial_thread.is_alive() and time.monotonic() - started <= args.observe_timeout:
        index += 1
        sample_started = time.monotonic()
        samples.append(capture_focused_sample(args, store, index, "during", True))
        sleep_for = args.sample_interval - (time.monotonic() - sample_started)
        if sleep_for > 0:
            time.sleep(sleep_for)
    return samples


def serial_start_summary(result: side.SerialRunResult | None) -> dict[str, Any] | None:
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


def signal_deltas(samples: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str], bool]:
    baseline = next((item for item in samples if item.get("phase") == "before"), None)
    if baseline is None:
        return [], [], False
    base_signals = baseline.get("signals") or {}
    deltas: list[dict[str, Any]] = []
    new_focus_lines: list[str] = []
    seen_lines: set[str] = set()
    wlan_surface = False
    state_labels = [label for label in base_signals if label not in {"ping", "status"}]
    base_focus: set[str] = set()
    for signal in base_signals.values():
        base_focus.update(str(line) for line in signal.get("focus_tail", []))
    for sample in samples:
        signals = sample.get("signals") or {}
        if sample.get("phase") in {"during", "after"}:
            for label in state_labels:
                base_hash = (base_signals.get(label) or {}).get("hash")
                current = signals.get(label) or {}
                if current.get("wlan_surface"):
                    wlan_surface = True
                if base_hash is not None and current.get("hash") != base_hash:
                    deltas.append(
                        {
                            "phase": sample.get("phase"),
                            "sample": sample.get("index"),
                            "label": label,
                            "before_hash": base_hash,
                            "after_hash": current.get("hash"),
                            "after_focus_tail": current.get("focus_tail", []),
                        }
                    )
                for line in current.get("focus_tail", []):
                    if line in base_focus or line in seen_lines:
                        continue
                    seen_lines.add(line)
                    new_focus_lines.append(str(line))
        else:
            for current in signals.values():
                if current.get("wlan_surface"):
                    wlan_surface = True
    return deltas, new_focus_lines, wlan_surface


def build_comparison(manifest: dict[str, Any]) -> dict[str, Any]:
    samples = manifest.get("samples") or []
    deltas, new_focus_lines, wlan_surface = signal_deltas(samples)
    postflight = manifest.get("postflight") or {}
    during_sample_ok = any(
        item.get("phase") == "during"
        and item.get("during_serial_run")
        and item.get("ok_count", 0) > 0
        for item in samples
    )
    focused_delta_count = len(deltas)
    return {
        "during_sample_ok": during_sample_ok,
        "sample_count": len(samples),
        "focused_delta_count": focused_delta_count,
        "focused_deltas_tail": deltas[-20:],
        "new_focus_line_count": len(new_focus_lines),
        "new_focus_lines_tail": new_focus_lines[-20:],
        "wlan_surface_visible": wlan_surface,
        "postflight_process_clean": bool(postflight.get("clean", True)),
    }


def classify(manifest: dict[str, Any]) -> tuple[bool, str, str]:
    sidechannel = manifest["sidechannel"]
    if manifest["mode"] == "plan":
        return True, "icnss-qca6390-focused-plan-ready", "documented focused during-start sampler without live execution"
    if not sidechannel.get("tcpctl_ready"):
        return False, "icnss-qca6390-focused-sidechannel-blocked", "NCM/tcpctl side-channel is not ready"
    if not sidechannel.get("host_ping_ok"):
        return False, "icnss-qca6390-focused-host-ncm-blocked", "host NCM ping did not pass"
    if manifest["mode"] == "preflight":
        return True, "icnss-qca6390-focused-preflight-ready", "NCM/tcpctl side-channel is reachable; no daemon executed"

    serial = manifest.get("serial_start") or {}
    if not serial.get("ok"):
        return False, "icnss-qca6390-focused-start-failed", "serial CNSS start-only command failed"
    helper_result = ((serial.get("cnss_start") or {}).get("result")) or "missing"
    if helper_result != "start-only-pass":
        return False, "icnss-qca6390-focused-start-not-pass", f"helper result is {helper_result}"
    comparison = manifest.get("comparison") or {}
    if not comparison.get("postflight_process_clean"):
        return False, "icnss-qca6390-focused-process-leak", "postflight CNSS process table is not clean"
    if not comparison.get("during_sample_ok"):
        return False, "icnss-qca6390-focused-unproven", "no focused sample completed while serial start-only was active"
    if comparison.get("wlan_surface_visible"):
        return False, "icnss-qca6390-focused-wlan-surface-leak", "wlan/wiphy appeared during bounded start-only"
    if comparison.get("focused_delta_count", 0) > 0 or comparison.get("new_focus_line_count", 0) > 0:
        return True, "icnss-qca6390-focused-during-delta", "focused ICNSS/QCA6390 state changed during bounded start-only"
    return True, "icnss-qca6390-focused-no-during-delta", "focused side-channel worked but no ICNSS/QCA6390 delta appeared"


def render_summary(manifest: dict[str, Any]) -> str:
    sample_rows = []
    for sample in manifest.get("samples") or []:
        sample_rows.append([
            str(sample.get("index")),
            str(sample.get("phase")),
            "yes" if sample.get("during_serial_run") else "no",
            f"{sample.get('ok_count', 0)}/{sample.get('capture_count', 0)}",
            f"{sample.get('duration_sec', 0.0):.3f}s",
        ])
    delta_rows = [
        [
            str(item.get("phase")),
            str(item.get("sample")),
            str(item.get("label")),
            str(item.get("after_hash", ""))[:12],
        ]
        for item in (manifest.get("comparison") or {}).get("focused_deltas_tail", [])
    ]
    capture_rows = [
        [item["label"], item["channel"], "PASS" if item["ok"] else "FAIL", item["status"]]
        for item in manifest.get("captures", [])
    ]
    comparison = manifest.get("comparison") or {}
    lines = [
        "# ICNSS/QCA6390 Focused During-Start Sampler\n\n",
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
        "\n\n## Focused Samples\n\n",
        markdown_table(["sample", "phase", "during", "ok", "duration"], sample_rows),
        "\n\n## Focused Deltas\n\n",
        markdown_table(["phase", "sample", "label", "hash"], delta_rows if delta_rows else [["none", "", "", ""]]),
        "\n\n## Comparison\n\n",
        f"- during_sample_ok: `{comparison.get('during_sample_ok')}`\n",
        f"- focused_delta_count: `{comparison.get('focused_delta_count')}`\n",
        f"- new_focus_line_count: `{comparison.get('new_focus_line_count')}`\n",
        f"- wlan_surface_visible: `{comparison.get('wlan_surface_visible')}`\n",
        f"- postflight_process_clean: `{comparison.get('postflight_process_clean')}`\n\n",
        "## Guardrails\n\n",
    ]
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    captures: list[side.Capture] = []
    sidechannel: dict[str, Any] = {
        "initial_tcpctl_ready": False,
        "initial_netservice_running": False,
        "started_netservice": False,
        "tcpctl_ready": False,
        "host_ping_ok": False,
    }
    samples: list[dict[str, Any]] = []
    serial_result: side.SerialRunResult | None = None
    daemon_start_executed = False
    postflight: dict[str, Any] = {"clean": True}

    if args.command != "plan":
        sidechannel = side.ensure_tcp_sidechannel(args, store, captures)

    if args.command in {"preflight", "run"} and sidechannel.get("tcpctl_ready") and sidechannel.get("host_ping_ok"):
        samples.append(capture_focused_sample(args, store, 0, "before", False))

    if args.command == "run" and sidechannel.get("tcpctl_ready") and sidechannel.get("host_ping_ok"):
        result_box: dict[str, side.SerialRunResult] = {}
        thread = side.serial_start_thread(args, store, result_box)
        daemon_start_executed = True
        time.sleep(args.initial_observe_delay)
        samples.extend(sample_during_run(args, store, thread, 0))
        thread.join(args.timeout + args.max_runtime_sec + 25.0)
        serial_result = result_box.get("serial")
        samples.append(capture_focused_sample(args, store, len(samples), "after", False))
        postflight_capture = side.serial_capture(
            args,
            store,
            "post-cnss-processes",
            ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm"],
            timeout=args.timeout,
            allow_error=True,
            retry_unsafe=True,
        )
        captures.append(postflight_capture)
        post_text = side.file_text(postflight_capture.file)
        postflight = {
            "clean": "cnss-daemon" not in post_text and "cnss_diag" not in post_text,
            "capture": asdict(postflight_capture),
        }

    side.stop_started_netservice(args, store, captures, sidechannel)
    manifest: dict[str, Any] = {
        "created": now_iso(),
        "mode": args.command,
        "host_metadata": collect_host_metadata(),
        "out_dir": str(out_dir),
        "daemon_start_executed": daemon_start_executed,
        "wifi_packet_transmission": False,
        "usb_ncm_control_packets": args.command != "plan",
        "qmi_payload": False,
        "qrtr_nameservice_packet": False,
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
            "no debugfs mount",
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
    parser.add_argument("--max-runtime-sec", type=int, default=15)
    parser.add_argument("--observe-timeout", type=float, default=24.0)
    parser.add_argument("--sample-interval", type=float, default=1.0)
    parser.add_argument("--initial-observe-delay", type=float, default=0.2)
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
