#!/usr/bin/env python3
"""V1176 host-only classifier for PM-service state-3/dependency gap.

This consumes V1175 live evidence and the extracted vendor `pm-service` binary.
It does not contact the device and does not execute PM actors, mdm_helper,
Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, or any
partition write.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1176-pm-state3-dependency-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1176-pm-state3-dependency-classifier.txt")
DEFAULT_V1175 = Path("tmp/wifi/v1175-pm-ack-fd-target-live-after-v490/manifest.json")
DEFAULT_V1165 = Path("tmp/wifi/v1165-late-per-proxy-actionability-live-after-v490/manifest.json")
DEFAULT_V1159_ROOT = Path("tmp/wifi/v1159-pm-thread-sampler-live-20260527-191019")
DEFAULT_PM_SERVICE = Path("tmp/wifi/v1073-host-only/vendor-extract/files/pm-service")
TIME_RE = re.compile(r"\s(?P<time>\d+\.\d+):\s+(?P<label>pm_ack_[^:]+):")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1175", type=Path, default=DEFAULT_V1175)
    parser.add_argument("--v1165", type=Path, default=DEFAULT_V1165)
    parser.add_argument("--v1159-root", type=Path, default=DEFAULT_V1159_ROOT)
    parser.add_argument("--pm-service", type=Path, default=DEFAULT_PM_SERVICE)
    parser.add_argument("--objdump", default="aarch64-linux-gnu-objdump")
    return parser.parse_args()


def read_text(path: Path, limit: int = 8_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def intish(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass", "running"}


def nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def event_time(event: dict[str, Any]) -> float | None:
    line = str(event.get("line", ""))
    match = TIME_RE.search(line)
    return float(match.group("time")) if match else None


def parse_invocations(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    invocations: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for event in events:
        label = str(event.get("label", ""))
        values = event.get("values") if isinstance(event.get("values"), dict) else {}
        if label == "pm_ack_impl_entry":
            if current:
                invocations.append(current)
            current = {
                "state": intish(values.get("state"), -1),
                "time": event_time(event),
                "labels": [],
                "current_states": [],
                "set_states": [],
                "dependency_flags": [],
                "open_results": [],
            }
        if current is None:
            continue
        current["labels"].append(label)
        if label == "pm_ack_state_current":
            current["current_states"].append(intish(values.get("current_state"), -1))
        elif label == "pm_ack_state_set_call":
            current["set_states"].append(intish(values.get("state"), -1))
        elif label == "pm_ack_state2_dependency_flag":
            current["dependency_flags"].append(intish(values.get("dependency_flag"), -1))
        elif label == "pm_ack_state2_open_result":
            current["open_results"].append(intish(values.get("fd"), -1))
        elif label == "pm_ack_state_core_ret":
            invocations.append(current)
            current = None
    if current:
        invocations.append(current)
    return invocations


def summarize_v1175(data: dict[str, Any]) -> dict[str, Any]:
    trace = nested(data, "analysis", "tracefs_uprobe") or {}
    body = trace.get("pm_ack_impl_body") if isinstance(trace, dict) else {}
    fds = trace.get("pm_ack_fd_targets") if isinstance(trace, dict) else {}
    body = body if isinstance(body, dict) else {}
    fds = fds if isinstance(fds, dict) else {}
    events = body.get("events") if isinstance(body.get("events"), list) else []
    invocations = parse_invocations(events)
    state2_times = [item["time"] for item in invocations if item.get("state") == 2 and item.get("time") is not None]
    state0_times = [item["time"] for item in invocations if item.get("state") == 0 and item.get("time") is not None]
    state0_delay_sec = None
    if state2_times and state0_times:
        state0_delay_sec = round(state0_times[0] - state2_times[0], 6)
    state3_noop = any(
        item.get("state") == 3
        and 3 in item.get("current_states", [])
        and not item.get("set_states")
        and "pm_ack_state2_open_call" not in item.get("labels", [])
        for item in invocations
    )
    state0_sets_state1 = any(item.get("state") == 0 and 1 in item.get("set_states", []) for item in invocations)
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "core_states": body.get("core_states", []),
        "current_states": body.get("current_states", []),
        "set_states": body.get("set_states", []),
        "dependency_flag_values": body.get("dependency_flag_values", []),
        "dependency_values": body.get("dependency_values", []),
        "open_ret_signed": body.get("open_ret_signed", []),
        "fd8_targets": fds.get("fd8_targets", []),
        "has_fd8_subsys_modem": bool(fds.get("has_fd8_subsys_modem")),
        "has_fd8_subsys_esoc0": bool(fds.get("has_fd8_subsys_esoc0")),
        "has_subsys_esoc0": bool(fds.get("has_subsys_esoc0")),
        "invocations": invocations,
        "state_order": [item.get("state") for item in invocations],
        "state0_delay_sec": state0_delay_sec,
        "state3_noop": state3_noop,
        "state0_sets_state1": state0_sets_state1,
    }


def summarize_v1165(data: dict[str, Any]) -> dict[str, Any]:
    trace = nested(data, "analysis", "tracefs_uprobe") or {}
    pm = trace.get("pm_service_trigger_observer") if isinstance(trace, dict) else {}
    pm = pm if isinstance(pm, dict) else {}
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "late_started": pm.get("late_per_proxy.started", pm.get("late_per_proxy_started", "")),
        "late_poll_count": pm.get("late_per_proxy_poll_count", ""),
        "trace_result": trace.get("result", "") if isinstance(trace, dict) else "",
    }


def dmesg_time(text: str, pattern: str) -> float | None:
    regex = re.compile(r"\[\s*(?P<time>\d+\.\d+)\].*" + pattern)
    for line in text.splitlines():
        match = regex.search(line)
        if match:
            return float(match.group("time"))
    return None


def summarize_android(v1159_root: Path) -> dict[str, Any]:
    root = repo_path(v1159_root)
    manifest = load_json(root / "manifest.json")
    extracted = root / "android-trace" / "extracted" / "a90-wifi"
    dmesg = read_text(extracted / "boot_dmesg.txt")
    times = {
        "per_proxy_start": dmesg_time(dmesg, r"starting service 'vendor\.per_proxy'"),
        "pm_service_modem_get": dmesg_time(dmesg, r"Binder:\d+_2:.*__subsystem_get: modem count:1"),
        "pm_service_esoc0_get": dmesg_time(dmesg, r"Binder:\d+_2:.*__subsystem_get: esoc0 count:0"),
        "fw_ready": dmesg_time(dmesg, r"FW ready event received"),
        "wlan0": dmesg_time(dmesg, r"dev : wlan0 : event : 16"),
    }
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "times": times,
        "esoc0_after_modem_sec": (
            round(times["pm_service_esoc0_get"] - times["pm_service_modem_get"], 6)
            if times["pm_service_esoc0_get"] is not None and times["pm_service_modem_get"] is not None
            else None
        ),
        "wlan0_seen": times["wlan0"] is not None,
    }


def disassemble(pm_service: Path, objdump: str) -> dict[str, Any]:
    resolved = repo_path(pm_service)
    tool = shutil.which(objdump)
    if not tool or not resolved.exists():
        return {"available": False, "tool": objdump, "text": "", "checks": {}}
    result = subprocess.run(
        [tool, "-d", "--start-address=0x8788", "--stop-address=0x8d20", str(resolved)],
        check=False,
        capture_output=True,
        text=True,
    )
    text = result.stdout + result.stderr
    checks = {
        "state2_dependency_ptr_load": "f940a696" in text and "[x20, #328]" in text,
        "state2_dependency_flag_load": "39450288" in text and "[x20, #320]" in text,
        "state2_dependency_flag_zero_skips_dependency": "340004e8" in text and "8988" in text,
        "dependency_state2_call": "52800041" in text and "bl\t92dc" in text,
        "state3_falls_through_to_return": "7100091f" in text and "8d1c" in text,
        "state0_sets_dependency_flag": "39050298" in text and "[x20, #320]" in text,
        "state0_sets_state1": "52800021" in text and "8d14" in text,
    }
    return {
        "available": result.returncode == 0,
        "tool": tool,
        "returncode": result.returncode,
        "text": text,
        "checks": checks,
    }


def classify(analysis: dict[str, Any]) -> dict[str, Any]:
    v1175 = analysis["v1175"]
    android = analysis["android_v1159"]
    disasm = analysis["pm_service_disassembly"]
    checks = disasm.get("checks") or {}
    flags = {
        "v1175_passed": v1175["pass"] and v1175["decision"] == "v1175-state2-opened-subsys-modem-not-esoc0",
        "state2_fd8_is_modem_not_esoc0": v1175["has_fd8_subsys_modem"] and not v1175["has_fd8_subsys_esoc0"],
        "state2_dependency_flag_zero": 0 in [intish(value, -1) for value in v1175["dependency_flag_values"]],
        "state3_current_seen_noop": bool(v1175["state3_noop"]),
        "state0_late_sets_state1": bool(v1175["state0_sets_state1"]),
        "android_esoc0_positive": bool(android["pass"] and android["times"]["pm_service_esoc0_get"] is not None and android["wlan0_seen"]),
        "disassembly_supports_dependency_branch": bool(
            checks.get("state2_dependency_flag_zero_skips_dependency")
            and checks.get("dependency_state2_call")
            and checks.get("state3_falls_through_to_return")
            and checks.get("state0_sets_dependency_flag")
        ),
    }
    missing = [name for name, ok in flags.items() if not ok]
    if not missing:
        return {
            "decision": "v1176-dependency-flag-state-order-gap-classified",
            "pass": True,
            "reason": (
                "V1175 shows the native state-2 PM ack opens only /dev/subsys_modem, "
                "skips the dependency path because dependency_flag is zero, and the "
                "following state-3 invocation is a no-op; Android-good still reaches "
                "pm-service __subsystem_get(esoc0), so the gap is PM dependency flag/state-order parity"
            ),
            "next_step": (
                "V1177 should trace the PM-service state-0/dependency-flag setter and Android/native state order, "
                "then repair ordering so dependency_flag is armed before the state-2 ack path; keep Wi-Fi HAL, "
                "scan/connect, credentials, DHCP/routes, and external ping blocked until eSoC/WLFW appears"
            ),
            "flags": flags,
            "missing": [],
        }
    return {
        "decision": "v1176-input-incomplete",
        "pass": False,
        "reason": "missing=" + ",".join(missing),
        "next_step": "refresh V1175/V1159 or pm-service disassembly before selecting the next gate",
        "flags": flags,
        "missing": missing,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    v1175 = analysis["v1175"]
    android = analysis["android_v1159"]
    disasm = analysis["pm_service_disassembly"]
    classification = analysis["classification"]
    rows = [
        ["V1175 decision", v1175["decision"], str(v1175["pass"])],
        ["state order", json.dumps(v1175["state_order"]), "native PM ack invocation order"],
        ["dependency flag values", json.dumps(v1175["dependency_flag_values"]), "state-2 branch input"],
        ["fd8 targets", json.dumps(v1175["fd8_targets"]), "opened fd target"],
        ["state3 noop", str(v1175["state3_noop"]), "current_state=3 returns without open/set"],
        ["state0 delay", str(v1175["state0_delay_sec"]), "seconds after first state=2"],
        ["state0 sets state1", str(v1175["state0_sets_state1"]), "late reset path observed"],
        ["Android esoc0 get", str(android["times"]["pm_service_esoc0_get"]), "Android-good lower trigger"],
        ["Android wlan0", str(android["times"]["wlan0"]), "Android-good Wi-Fi lower chain"],
    ]
    disasm_rows = [[key, str(value)] for key, value in sorted((disasm.get("checks") or {}).items())]
    return "\n".join([
        "# V1176 PM State3 Dependency Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Classification",
        "",
        markdown_table(["evidence", "value", "detail"], rows),
        "",
        "## PM-Service Disassembly Checks",
        "",
        markdown_table(["check", "ok"], disasm_rows),
        "",
        "## Missing",
        "",
        json.dumps(classification["missing"], indent=2, sort_keys=True),
        "",
        "## Safety",
        "",
        "- device commands executed: `false`",
        "- PM actors, mdm_helper, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping: `false`",
        "- boot image/partition writes/flash: `false`",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = {
        "v1175": summarize_v1175(load_json(args.v1175)),
        "v1165": summarize_v1165(load_json(args.v1165)),
        "android_v1159": summarize_android(args.v1159_root),
        "pm_service_disassembly": disassemble(args.pm_service, args.objdump),
    }
    classification = classify(analysis)
    analysis["classification"] = classification
    manifest = {
        "cycle": "v1176",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1175": str(repo_path(args.v1175)),
            "v1165": str(repo_path(args.v1165)),
            "v1159_root": str(repo_path(args.v1159_root)),
            "pm_service": str(repo_path(args.pm_service)),
        },
        "analysis": analysis,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
        "pm_actor_executed": False,
        "mdm_helper_executed": False,
        "tracefs_write_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    store.write_text("host/pm-service-state-machine-disassembly.txt", analysis["pm_service_disassembly"].get("text", ""))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
