#!/usr/bin/env python3
"""V1296 host-only classifier for the V1295 dense-window early exit.

V1295 intended a 40-sample, 50 ms dense response window. The manifest only
contains 14 parsed samples. This classifier determines whether that was a real
observer early exit or an evidence-capture truncation before selecting the next
gate.

No device command is executed here.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1296-dense-window-early-exit-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1296-dense-window-early-exit-classifier.txt")
DEFAULT_V1295_MANIFEST = Path("tmp/wifi/v1295-dense-response-sampler-live/manifest.json")
DEFAULT_V1295_TRANSCRIPT = Path("tmp/wifi/v1295-dense-response-sampler-live/host/pm-server-wchan-tracefs-observer.txt")
TRUNCATION_RE = re.compile(r"A90_EXECNS_STDOUT_END truncated=(\d+) bytes=(\d+)")
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
SAMPLE_BEGIN_RE = re.compile(r"pm_service_trigger_observer\.response_sample\.([^.]+)\.begin=1")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1295-manifest", type=Path, default=DEFAULT_V1295_MANIFEST)
    parser.add_argument("--v1295-transcript", type=Path, default=DEFAULT_V1295_TRANSCRIPT)
    parser.add_argument("command", nargs="?", choices=("run",), default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, max(offset, 0)) + 1


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def transcript_analysis(text: str) -> dict[str, Any]:
    keys = parse_key_values(text)
    truncation_match = TRUNCATION_RE.search(text)
    sample_matches = list(SAMPLE_BEGIN_RE.finditer(text))
    sample_phases = [match.group(1) for match in sample_matches]
    unique_phases = ordered_unique(sample_phases)
    truncation_offset = truncation_match.start() if truncation_match else -1
    poll13_before_truncation = False
    poll13_line = None
    if truncation_offset >= 0:
        poll13_offset = text.rfind("late_per_proxy_poll_13", 0, truncation_offset)
        poll13_before_truncation = poll13_offset >= 0
        poll13_line = line_number(text, poll13_offset) if poll13_offset >= 0 else None
    return {
        "exists": bool(text),
        "bytes": len(text.encode("utf-8")),
        "line_count": text.count("\n") + (1 if text else 0),
        "stdout_truncated": truncation_match is not None and truncation_match.group(1) == "1",
        "stdout_truncated_bytes": int_value(truncation_match.group(2) if truncation_match else None, -1),
        "stdout_truncation_line": line_number(text, truncation_offset) if truncation_offset >= 0 else None,
        "sample_begin_occurrences": len(sample_matches),
        "unique_sample_count": len(unique_phases),
        "unique_sample_phases": unique_phases,
        "response_sampler_begin": keys.get("pm_service_trigger_observer.response_sampler.begin") == "1",
        "response_sampler_end": keys.get("pm_service_trigger_observer.response_sampler.end") == "1",
        "response_sampler_mode": keys.get("pm_service_trigger_observer.response_sampler.mode", ""),
        "response_sampler_poll_max": int_value(keys.get("pm_service_trigger_observer.response_sampler.poll_max"), -1),
        "response_sampler_interval_ms": int_value(keys.get("pm_service_trigger_observer.response_sampler.sample_interval_ms"), -1),
        "dense_enabled": keys.get("pm_service_trigger_observer.response_sampler.dense_enabled") == "1",
        "dense_sample_count": int_value(keys.get("pm_service_trigger_observer.response_sampler.dense_sample_count"), -1),
        "dense_interval_ms": int_value(keys.get("pm_service_trigger_observer.response_sampler.dense_sample_interval_ms"), -1),
        "dense_window_ms": int_value(keys.get("pm_service_trigger_observer.response_sampler.dense_window_ms"), -1),
        "poll13_seen_before_truncation": poll13_before_truncation,
        "poll13_line": poll13_line,
        "run_exit_zero": "[exit 0]" in text,
        "cmdv1_run_ok": "A90P1 END" in text and "cmd=run rc=0" in text and "status=ok" in text,
        "helper_stdout_end_marker": "A90_EXECNS_STDOUT_END" in text,
        "helper_execns_end_rc0": "A90_EXECNS_END rc=0" in text,
        "pm_service_esoc0_attempt": "/dev/subsys_esoc0" in text and "mdm_subsys_powerup" in text,
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v1295_manifest)
    transcript = transcript_analysis(read_text(args.v1295_transcript))
    sampler = manifest.get("response_sampler") or {}
    pm = manifest.get("pm_service_trigger_observer") or {}
    manifest_sample_count = int_value(sampler.get("sample_count"), -1)
    manifest_mode = str(sampler.get("mode", ""))
    manifest_ended = bool_value(sampler.get("ended"))
    manifest_pm_esoc0 = bool_value(pm.get("pm_service_actor_esoc0_attempt"))
    output_cap_blocker = (
        bool_value(manifest.get("pass"))
        and manifest_sample_count == 14
        and manifest_mode == "late-per-proxy-dense-pinctrl-irq-pcie"
        and transcript["stdout_truncated"]
        and transcript["stdout_truncated_bytes"] == 1_048_576
        and transcript["dense_enabled"]
        and transcript["dense_sample_count"] == 40
        and transcript["poll13_seen_before_truncation"]
        and not transcript["response_sampler_end"]
        and transcript["run_exit_zero"]
        and transcript["cmdv1_run_ok"]
    )
    if output_cap_blocker:
        decision = "v1296-dense-window-limited-by-helper-stdout-cap"
        passed = True
        reason = "V1295 dense observer did not prove a 14-sample runtime stop; helper stdout was truncated at 1048576 bytes during poll_13"
        next_step = "V1297 source/build-only compact dense sampler or file-backed evidence path below the helper stdout cap"
    else:
        decision = "v1296-dense-window-early-exit-review"
        passed = False
        reason = "V1295 evidence does not cleanly prove stdout-cap truncation as the early-exit cause"
        next_step = "inspect raw V1295 transcript and parser assumptions before another live run"
    return {
        "cycle": "v1296",
        "generated_at": now_iso(),
        "command": "run",
        "host": collect_host_metadata(),
        "inputs": {
            "v1295_manifest": str(repo_path(args.v1295_manifest)),
            "v1295_transcript": str(repo_path(args.v1295_transcript)),
        },
        "manifest_summary": {
            "decision": manifest.get("decision", ""),
            "pass": bool_value(manifest.get("pass")),
            "reason": manifest.get("reason", ""),
            "response_sampler_mode": manifest_mode,
            "response_sampler_sample_count": manifest_sample_count,
            "response_sampler_ended": manifest_ended,
            "pm_service_actor_esoc0_attempt": manifest_pm_esoc0,
            "max_mdm_status_count_total": int_value(sampler.get("max_mdm_status_count_total"), -1),
            "max_mhi_bus_count": int_value(sampler.get("max_mhi_bus_count"), -1),
            "mhi_pipe_seen": bool_value(sampler.get("mhi_pipe_seen")),
            "wlan0_seen": bool_value(sampler.get("wlan0_seen")),
        },
        "transcript": transcript,
        "safety": {
            "host_only": True,
            "device_command_executed": False,
            "live_actor_started": False,
            "pmic_write_executed": False,
            "gpio_line_request_executed": False,
            "direct_esoc_ioctl_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "flash_or_partition_write_executed": False,
        },
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    transcript = manifest["transcript"]
    summary = manifest["manifest_summary"]
    rows = [
        ["decision", manifest["decision"]],
        ["pass", str(manifest["pass"]).lower()],
        ["manifest sample count", str(summary["response_sampler_sample_count"])],
        ["manifest sampler ended", str(summary["response_sampler_ended"]).lower()],
        ["transcript stdout truncated", str(transcript["stdout_truncated"]).lower()],
        ["truncated bytes", str(transcript["stdout_truncated_bytes"])],
        ["dense sample count", str(transcript["dense_sample_count"])],
        ["unique parsed phases", str(transcript["unique_sample_count"])],
        ["poll_13 before truncation", str(transcript["poll13_seen_before_truncation"]).lower()],
        ["helper run exit zero", str(transcript["run_exit_zero"]).lower()],
        ["cmdv1 run ok", str(transcript["cmdv1_run_ok"]).lower()],
        ["pm-service eSoC attempt", str(transcript["pm_service_esoc0_attempt"]).lower()],
    ]
    return "\n".join([
        "# V1296 Dense Window Early-Exit Classifier",
        "",
        markdown_table(["key", "value"], rows),
        "",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = analyze(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(repo_path(args.out_dir)) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"next:     {manifest['next_step']}")
    print(f"evidence: {repo_path(args.out_dir)}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
