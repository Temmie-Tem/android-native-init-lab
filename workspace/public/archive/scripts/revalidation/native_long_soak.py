#!/usr/bin/env python3
"""Observe native-init host/device stability for a bounded long-soak window."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
sys.path.insert(0, str(Path(__file__).resolve().parent))

from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402

DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.53 (v153)"
DEFAULT_DEVICE_EXPORT_MAX_LINES = 200000
DEFAULT_DEVICE_EXPORT_MAX_BYTES = 16 * 1024 * 1024


@dataclass
class HostSample:
    type: str
    seq: int
    host_ts: float
    command: str
    ok: bool
    duration_sec: float
    protocol_rc: int | None
    protocol_status: str
    error: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="serial bridge host")
    parser.add_argument("--port", type=int, default=54321, help="serial bridge TCP port")
    parser.add_argument("--duration-sec", type=int, default=60, help="host observation duration")
    parser.add_argument("--interval", type=float, default=10.0, help="host command interval")
    parser.add_argument("--timeout", type=float, default=20.0, help="per-command timeout")
    parser.add_argument("--device-interval", type=int, default=60, help="device recorder interval")
    parser.add_argument("--device-export-max-lines", type=int, default=DEFAULT_DEVICE_EXPORT_MAX_LINES)
    parser.add_argument("--device-export-max-bytes", type=int, default=DEFAULT_DEVICE_EXPORT_MAX_BYTES)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--start-device", action="store_true", help="start device longsoak recorder first")
    parser.add_argument("--no-stop-device", action="store_true", help="leave device recorder running")
    parser.add_argument("--out", default="tmp/soak/native-long-soak-v153.txt")
    parser.add_argument("--jsonl-out", default="tmp/soak/native-long-soak-v153-host.jsonl")
    parser.add_argument("--device-jsonl-out", default="tmp/soak/native-long-soak-v153-device.jsonl")
    parser.add_argument("--summary-json", default="tmp/soak/native-long-soak-v153-summary.json")
    return parser.parse_args()


def run_device_command(args: argparse.Namespace, command: list[str]) -> tuple[ProtocolResult | None, float, str]:
    started = time.monotonic()
    try:
        result = run_cmdv1_command(
            args.host,
            args.port,
            args.timeout,
            command,
            retry_unsafe=False,
        )
        return result, time.monotonic() - started, ""
    except Exception as exc:  # noqa: BLE001 - validation script records exact failure text
        return None, time.monotonic() - started, str(exc)


def write_jsonl(path: Path, payload: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def record_command(args: argparse.Namespace,
                   jsonl_path: Path,
                   seq: int,
                   command: list[str]) -> tuple[HostSample, str]:
    result, duration, error = run_device_command(args, command)
    command_text = " ".join(command)
    text = result.text if result is not None else ""
    protocol_rc = result.rc if result is not None else None
    protocol_status = result.status if result is not None else "missing"
    ok = result is not None and protocol_rc == 0 and protocol_status == "ok"

    if command == ["version"] and args.expect_version not in text:
        ok = False
        error = (error + "; " if error else "") + f"missing expected version {args.expect_version!r}"
    if command == ["status"] and "selftest: pass=" not in text:
        ok = False
        error = (error + "; " if error else "") + "status missing selftest summary"
    if command[:2] == ["longsoak", "status"] and ("longsoak:" not in text or "running=" not in text):
        ok = False
        error = (error + "; " if error else "") + "longsoak status missing running state"

    sample = HostSample(
        type="host_command",
        seq=seq,
        host_ts=time.time(),
        command=command_text,
        ok=ok,
        duration_sec=duration,
        protocol_rc=protocol_rc,
        protocol_status=protocol_status,
        error=error,
    )
    payload = asdict(sample)
    if result is not None:
        payload["begin"] = result.begin
        payload["end"] = result.end
    write_jsonl(jsonl_path, payload)
    return sample, text


def append_summary(lines: list[str], sample: HostSample) -> None:
    state = "PASS" if sample.ok else "FAIL"
    lines.append(
        f"- {state} seq={sample.seq} cmd=`{sample.command}` "
        f"duration={sample.duration_sec:.3f}s rc={sample.protocol_rc} "
        f"status={sample.protocol_status}"
    )
    if sample.error:
        lines[-1] += f" error={sample.error}"
    lines[-1] += "\n"


def extract_device_jsonl(text: str) -> list[str]:
    lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            lines.append(stripped)
    return lines


def extract_longsoak_path(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("longsoak: path="):
            path = line.split("=", 1)[1].strip()
            if path and path != "-":
                return path
        if line.startswith("/"):
            return line.strip()
    return None


def parse_longsoak_export_summary(text: str) -> dict[str, str]:
    prefix = "longsoak: export "
    summary: dict[str, str] = {}

    for line in text.splitlines():
        if not line.startswith(prefix):
            continue
        for token in line[len(prefix):].split():
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            summary[key] = value
    return summary


def main() -> int:
    args = parse_args()
    if args.duration_sec < 1:
        raise SystemExit("--duration-sec must be >= 1")
    if args.interval <= 0:
        raise SystemExit("--interval must be > 0")

    out_path = Path(args.out)
    jsonl_path = Path(args.jsonl_out)
    device_jsonl_path = Path(args.device_jsonl_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    device_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.write_text("", encoding="utf-8")
    device_jsonl_path.write_text("", encoding="utf-8")

    lines: list[str] = []
    lines.append("# Native Long Soak Observation\n")
    lines.append(f"expect_version={args.expect_version}\n")
    lines.append(f"duration_sec={args.duration_sec} interval={args.interval}\n")
    lines.append(f"device_interval={args.device_interval} start_device={args.start_device}\n")
    lines.append(f"jsonl={jsonl_path}\n\n")

    failures = 0
    seq = 0
    ok_count = 0
    max_duration = 0.0

    if args.start_device:
        sample, _ = record_command(
            args,
            jsonl_path,
            seq,
            ["longsoak", "start", str(args.device_interval)],
        )
        append_summary(lines, sample)
        failures += 0 if sample.ok else 1
        ok_count += 1 if sample.ok else 0
        max_duration = max(max_duration, sample.duration_sec)
        seq += 1

    deadline = time.monotonic() + args.duration_sec
    commands = [
        ["version"],
        ["status"],
        ["longsoak", "status", "verbose"],
    ]
    while time.monotonic() < deadline:
        for command in commands:
            sample, _ = record_command(args, jsonl_path, seq, command)
            append_summary(lines, sample)
            failures += 0 if sample.ok else 1
            ok_count += 1 if sample.ok else 0
            max_duration = max(max_duration, sample.duration_sec)
            seq += 1
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(args.interval, remaining))

    sample, tail_text = record_command(args, jsonl_path, seq, ["longsoak", "tail", "5"])
    append_summary(lines, sample)
    failures += 0 if sample.ok else 1
    ok_count += 1 if sample.ok else 0
    max_duration = max(max_duration, sample.duration_sec)
    seq += 1
    lines.append("\n## Device Tail\n\n")
    lines.append(tail_text.rstrip() + "\n\n")

    if args.start_device and not args.no_stop_device:
        sample, _ = record_command(args, jsonl_path, seq, ["longsoak", "stop"])
        append_summary(lines, sample)
        failures += 0 if sample.ok else 1
        ok_count += 1 if sample.ok else 0
        max_duration = max(max_duration, sample.duration_sec)
        seq += 1

    sample, path_text = record_command(args, jsonl_path, seq, ["longsoak", "path"])
    append_summary(lines, sample)
    failures += 0 if sample.ok else 1
    ok_count += 1 if sample.ok else 0
    max_duration = max(max_duration, sample.duration_sec)
    seq += 1
    device_path = extract_longsoak_path(path_text)
    exported_device_lines: list[str] = []
    sample, _ = record_command(args, jsonl_path, seq, ["hide"])
    append_summary(lines, sample)
    failures += 0 if sample.ok else 1
    ok_count += 1 if sample.ok else 0
    max_duration = max(max_duration, sample.duration_sec)
    seq += 1
    sample, export_text = record_command(
        args,
        jsonl_path,
        seq,
        [
            "longsoak",
            "export",
            str(args.device_export_max_lines),
            str(args.device_export_max_bytes),
        ],
    )
    append_summary(lines, sample)
    failures += 0 if sample.ok else 1
    ok_count += 1 if sample.ok else 0
    max_duration = max(max_duration, sample.duration_sec)
    seq += 1
    export_summary = parse_longsoak_export_summary(export_text)
    if not export_summary:
        failures += 1
        lines.append("- FAIL device JSONL export summary unavailable\n")
    if device_path is None:
        failures += 1
        lines.append("- FAIL device JSONL path metadata unavailable\n")
    exported_device_lines = extract_device_jsonl(export_text)
    device_jsonl_path.write_text(
        "\n".join(exported_device_lines) + ("\n" if exported_device_lines else ""),
        encoding="utf-8",
    )

    out_path.write_text("".join(lines), encoding="utf-8")
    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "expect_version": args.expect_version,
                "samples": seq,
                "ok": ok_count,
                "failures": failures,
                "max_duration_sec": max_duration,
                "jsonl": str(jsonl_path),
                "device_jsonl": str(device_jsonl_path),
                "device_export_lines": len(exported_device_lines),
                "device_export_summary": export_summary,
                "device_path": device_path,
                "transcript": str(out_path),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    if failures:
        print(f"FAIL samples={seq} failures={failures}")
        print(out_path)
        print(jsonl_path)
        print(device_jsonl_path)
        print(summary_path)
        return 1

    print(f"PASS samples={seq} failures=0")
    print(out_path)
    print(jsonl_path)
    print(device_jsonl_path)
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
