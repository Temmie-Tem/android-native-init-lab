#!/usr/bin/env python3
"""Classify host/device disconnect symptoms using serial bridge, NCM ping, and longsoak evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402

DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.53 (v153)"
DEFAULT_DEVICE_IP = "192.168.7.2"


@dataclass
class ProbeResult:
    name: str
    ok: bool
    duration_sec: float
    detail: str
    rc: int | None = None
    status: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="serial bridge host")
    parser.add_argument("--port", type=int, default=54321, help="serial bridge TCP port")
    parser.add_argument("--timeout", type=float, default=12.0, help="cmdv1 timeout")
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP, help="USB NCM device IPv4")
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-md", default="tmp/soak/native-disconnect-v153.md")
    parser.add_argument("--out-json", default="tmp/soak/native-disconnect-v153.json")
    return parser.parse_args()


def run_cmd(args: argparse.Namespace, name: str, command: list[str]) -> tuple[ProbeResult, str]:
    started = time.monotonic()
    try:
        result: ProtocolResult = run_cmdv1_command(
            args.host,
            args.port,
            args.timeout,
            command,
            retry_unsafe=False,
        )
        duration = time.monotonic() - started
        ok = result.rc == 0 and result.status == "ok"
        detail = "ok" if ok else f"rc={result.rc} status={result.status}"
        return ProbeResult(name, ok, duration, detail, result.rc, result.status), result.text
    except Exception as exc:  # noqa: BLE001 - classifier records exact symptom text
        duration = time.monotonic() - started
        return ProbeResult(name, False, duration, str(exc), None, "missing"), ""


def run_ping(args: argparse.Namespace) -> ProbeResult:
    started = time.monotonic()
    cmd = ["ping", "-c", "1", "-W", "2", args.device_ip]
    try:
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=4)
        duration = time.monotonic() - started
        tail = " ".join(proc.stdout.strip().splitlines()[-2:]) if proc.stdout else ""
        return ProbeResult("ncm_ping", proc.returncode == 0, duration, tail, proc.returncode, None)
    except Exception as exc:  # noqa: BLE001
        duration = time.monotonic() - started
        return ProbeResult("ncm_ping", False, duration, str(exc), None, None)


def contains(text: str, needle: str) -> bool:
    return needle in text if text else False


def classify(probes: dict[str, ProbeResult], texts: dict[str, str]) -> str:
    bridge_ok = probes["version"].ok or probes["status"].ok
    version_ok = probes["version"].ok and contains(texts.get("version", ""), "A90 Linux init")
    status_ok = probes["status"].ok
    ncm_ok = probes["ncm_ping"].ok
    longsoak_ok = probes["longsoak"].ok
    longsoak_text = texts.get("longsoak", "")
    recorder_running = contains(longsoak_text, "running=yes")
    recorder_healthy = contains(longsoak_text, "health=ok") or contains(longsoak_text, "health=warming")

    if bridge_ok and ncm_ok and longsoak_ok:
        return "all-paths-ok"
    if bridge_ok and not ncm_ok:
        return "serial-ok-ncm-down-or-inactive"
    if not bridge_ok and ncm_ok:
        return "serial-bridge-down-ncm-ok"
    if not bridge_ok and recorder_running and recorder_healthy:
        return "host-control-down-device-recorder-alive"
    if version_ok or status_ok:
        return "partial-serial-control"
    return "device-or-usb-unreachable"


def write_outputs(args: argparse.Namespace,
                  probes: dict[str, ProbeResult],
                  texts: dict[str, str],
                  classification: str) -> None:
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "classification": classification,
        "expect_version": args.expect_version,
        "device_ip": args.device_ip,
        "probes": {name: asdict(probe) for name, probe in probes.items()},
        "version_matches": args.expect_version in texts.get("version", ""),
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Native Disconnect Classification\n\n",
        f"- classification: `{classification}`\n",
        f"- expect_version: `{args.expect_version}`\n",
        f"- version_matches: `{payload['version_matches']}`\n",
        f"- device_ip: `{args.device_ip}`\n\n",
        "## Probes\n\n",
        "| Probe | OK | Duration | RC | Status | Detail |\n",
        "|---|---:|---:|---:|---|---|\n",
    ]
    for probe in probes.values():
        detail = probe.detail.replace("|", "/").replace("\n", " ")[:160]
        lines.append(
            f"| `{probe.name}` | `{probe.ok}` | `{probe.duration_sec:.3f}s` | "
            f"`{probe.rc}` | `{probe.status}` | {detail} |\n"
        )
    out_md.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    probes: dict[str, ProbeResult] = {}
    texts: dict[str, str] = {}

    for name, command in (
        ("version", ["version"]),
        ("status", ["status"]),
        ("longsoak", ["longsoak", "status", "verbose"]),
        ("netservice", ["netservice", "status"]),
    ):
        probe, text = run_cmd(args, name, command)
        probes[name] = probe
        texts[name] = text
    probes["ncm_ping"] = run_ping(args)

    classification = classify(probes, texts)
    write_outputs(args, probes, texts, classification)
    print(f"classification={classification}")
    for probe in probes.values():
        print(f"{probe.name}: ok={probe.ok} duration={probe.duration_sec:.3f}s rc={probe.rc} status={probe.status} detail={probe.detail}")
    return 0 if probes["version"].ok and args.expect_version in texts.get("version", "") else 1


if __name__ == "__main__":
    raise SystemExit(main())
