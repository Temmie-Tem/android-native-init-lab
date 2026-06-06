#!/usr/bin/env python3
"""V1860 read-only native-init bridge smoke for Wi-Fi prerequisite gating."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1860"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1860-bridge-readonly-smoke"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1860_BRIDGE_READONLY_SMOKE_2026-06-03.md"
)
V1859_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1859-bridge-transport-locator" / "manifest.json"
A90CTL = REPO_ROOT / "scripts" / "revalidation" / "a90ctl.py"
DEFAULT_TIMEOUT = 8.0
PAYLOAD_LINE_LIMIT = 40
PAYLOAD_CHAR_LIMIT = 6000

READONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("status", ["status"], 10.0),
    ("bootstatus", ["bootstatus"], 10.0),
    ("selftest", ["selftest"], 10.0),
    ("netservice-status", ["netservice", "status"], 8.0),
    ("wifiinv-summary", ["wifiinv", "summary"], 8.0),
    ("wififeas-gate", ["wififeas", "gate"], 8.0),
    ("sys-class-net", ["ls", "/sys/class/net"], 8.0),
    ("wlan0-stat", ["stat", "/sys/class/net/wlan0"], 8.0),
    ("sys-class-ieee80211", ["ls", "/sys/class/ieee80211"], 8.0),
    ("proc-net-wireless", ["cat", "/proc/net/wireless"], 8.0),
    ("proc-net-qrtr", ["cat", "/proc/net/qrtr"], 8.0),
    ("debug-qrtr-ns", ["cat", "/sys/kernel/debug/qrtr/qrtr-ns"], 8.0),
)

SAFE_READONLY_COMMAND_NAMES = {
    "status",
    "bootstatus",
    "selftest",
    "netservice",
    "wifiinv",
    "wififeas",
    "ls",
    "stat",
    "cat",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def redact(text: str) -> str:
    redacted = re.sub(r"(made by)\s+[^\\\"\r\n]+", r"\1 [redacted]", text, flags=re.IGNORECASE)
    redacted = re.sub(r"\btemmie[A-Za-z0-9_.-]*\b", "[redacted-token]", redacted, flags=re.IGNORECASE)
    return redacted


def strip_protocol(text: str) -> str:
    payload: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("A90P1 BEGIN") or line.startswith("A90P1 END"):
            continue
        if line.startswith("a90:/#"):
            continue
        payload.append(line)
    return "\n".join(payload)


def truncated_lines(text: str, limit: int = PAYLOAD_LINE_LIMIT) -> list[str]:
    lines = clean_lines(text)
    if len(lines) <= limit:
        return lines
    return lines[:limit] + [f"[truncated {len(lines) - limit} lines]"]


def ensure_readonly_commands() -> None:
    unsafe = [
        command
        for _name, command, _timeout in READONLY_COMMANDS
        if not command or command[0] not in SAFE_READONLY_COMMAND_NAMES
    ]
    if unsafe:
        raise SystemExit(f"non-read-only command configured: {unsafe}")


def run_a90ctl(name: str, command: list[str], timeout: float) -> dict[str, Any]:
    python3 = shutil.which("python3")
    if not python3:
        return {
            "name": name,
            "command": command,
            "host_available": False,
            "host_rc": 127,
            "parsed_json": False,
            "protocol_rc": None,
            "protocol_status": "host-python3-missing",
            "payload": "",
            "payload_lines": [],
            "stderr_lines": ["python3 not found"],
        }

    host_command = [
        python3,
        str(A90CTL),
        "--json",
        "--allow-error",
        "--timeout",
        f"{timeout:.1f}",
        *command,
    ]
    try:
        completed = subprocess.run(
            host_command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 2.0,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = redact(exc.stdout or "")
        stderr = redact(exc.stderr or "timeout")
        return {
            "name": name,
            "command": command,
            "host_available": True,
            "host_rc": 124,
            "parsed_json": False,
            "protocol_rc": None,
            "protocol_status": "host-timeout",
            "payload": strip_protocol(stdout)[:PAYLOAD_CHAR_LIMIT],
            "payload_lines": truncated_lines(strip_protocol(stdout)),
            "stderr_lines": truncated_lines(stderr, 12),
        }

    stdout = completed.stdout
    stderr = redact(completed.stderr)
    parsed: dict[str, Any] | None = None
    try:
        loaded = json.loads(stdout)
        if isinstance(loaded, dict):
            parsed = loaded
    except json.JSONDecodeError:
        parsed = None

    text = str(parsed.get("text", "")) if parsed else redact(stdout)
    payload = strip_protocol(redact(text))
    if len(payload) > PAYLOAD_CHAR_LIMIT:
        payload = payload[:PAYLOAD_CHAR_LIMIT] + "\n[truncated]\n"
    end = parsed.get("end", {}) if parsed else {}
    return {
        "name": name,
        "command": command,
        "host_available": True,
        "host_rc": completed.returncode,
        "parsed_json": parsed is not None,
        "protocol_rc": parsed.get("rc") if parsed else None,
        "protocol_status": parsed.get("status") if parsed else "json-parse-failed",
        "begin": parsed.get("begin", {}) if parsed else {},
        "end": end if isinstance(end, dict) else {},
        "payload": payload,
        "payload_lines": truncated_lines(payload),
        "stderr_lines": truncated_lines(stderr, 12),
    }


def command_ok(record: dict[str, Any]) -> bool:
    return (
        bool(record.get("host_available"))
        and record.get("host_rc") == 0
        and bool(record.get("parsed_json"))
        and record.get("protocol_rc") == 0
        and record.get("protocol_status") == "ok"
    )


def find_record(records: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for record in records:
        if record.get("name") == name:
            return record
    return {}


def payload_text(records: list[dict[str, Any]], names: set[str] | None = None) -> str:
    selected = records if names is None else [record for record in records if record.get("name") in names]
    return "\n".join(str(record.get("payload", "")) for record in selected)


def wlan0_present(records: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    stat_record = find_record(records, "wlan0-stat")
    net_text = payload_text(records, {"sys-class-net", "wlan0-stat", "proc-net-wireless"})
    evidence: list[str] = []
    for line in clean_lines(net_text):
        if re.search(r"(^|[^A-Za-z0-9_])wlan0([^A-Za-z0-9_]|$)", line):
            evidence.append(line)
    stat_ok = command_ok(stat_record)
    no_such = any("No such file" in line or "No such file or directory" in line for line in clean_lines(net_text))
    return bool(stat_ok or (evidence and not no_such)), evidence[:12]


def wlfw_service69_present(records: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    text = payload_text(records, {"wifiinv-summary", "wififeas-gate", "proc-net-qrtr", "debug-qrtr-ns"})
    positive_lines: list[str] = []
    positive_patterns = (
        re.compile(r"\bwlfw\b.*\b(service\s*)?69\b.*\b(present|seen|found|online|up|published|true|1)\b", re.I),
        re.compile(r"\b(service\s*)?69\b.*\bwlfw\b.*\b(present|seen|found|online|up|published|true|1)\b", re.I),
        re.compile(r"\bwlfw[_ .-]*service[_ .-]*69[_ .-]*(seen|present|progress)\s*[:=]\s*(1|true|yes)", re.I),
        re.compile(r"\blower[_ .-]*service69[_ .-]*progress\s*[:=]\s*(1|true|yes)", re.I),
    )
    negative_re = re.compile(r"\b(absent|missing|not\s+found|false|no|none)\b", re.I)
    for line in clean_lines(text):
        if any(pattern.search(line) for pattern in positive_patterns) and not negative_re.search(line):
            positive_lines.append(line)
    return bool(positive_lines), positive_lines[:12]


def wifiinv_wlan_like_count(records: list[dict[str, Any]]) -> int | None:
    text = str(find_record(records, "wifiinv-summary").get("payload", ""))
    match = re.search(r"\bnet\s+total=\d+\s+wlan_like=(\d+)\b", text)
    return int(match.group(1)) if match else None


def wififeas_decision(records: list[dict[str, Any]]) -> str:
    text = str(find_record(records, "wififeas-gate").get("payload", ""))
    match = re.search(r"\bwififeas:\s+decision=([A-Za-z0-9_.+-]+)", text)
    return match.group(1) if match else ""


def collect_smoke(v1859: dict[str, Any]) -> dict[str, Any]:
    ensure_readonly_commands()
    git_status = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    records = [
        run_a90ctl(name, command, timeout)
        for name, command, timeout in READONLY_COMMANDS
    ]
    core_names = ("status", "bootstatus", "selftest")
    core_ok = {name: command_ok(find_record(records, name)) for name in core_names}
    wlan_present, wlan_lines = wlan0_present(records)
    wlfw_present, wlfw_lines = wlfw_service69_present(records)
    return {
        "v1859": {
            "path": rel(V1859_MANIFEST),
            "decision": v1859.get("decision", ""),
            "label": v1859.get("label", ""),
            "pass": bool(v1859.get("pass")),
        },
        "host": {
            "git_clean": git_status.returncode == 0 and git_status.stdout == "",
            "git_status_lines": clean_lines(git_status.stdout)[:20],
        },
        "commands": records,
        "summary": {
            "core_readonly_ok": all(core_ok.values()),
            "core_command_ok": core_ok,
            "successful_command_count": sum(1 for record in records if command_ok(record)),
            "total_command_count": len(records),
            "busy_command_count": sum(1 for record in records if record.get("protocol_status") == "busy"),
            "wifiinv_wlan_like_count": wifiinv_wlan_like_count(records),
            "wififeas_decision": wififeas_decision(records),
            "wlfw_service69_present": wlfw_present,
            "wlfw_service69_evidence": wlfw_lines,
            "wlan0_present": wlan_present,
            "wlan0_evidence": wlan_lines,
        },
        "safety": {
            "read_only_a90ctl_commands_executed": True,
            "a90ctl_version_command_executed": False,
            "serial_bridge_started": False,
            "flash_executed": False,
            "reboot_executed": False,
            "stage_properties_executed": False,
            "start_actors_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "direct_subsys_esoc0_open_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "esoc_ioctl_notify_executed": False,
            "forced_rc1_or_pci_rescan_executed": False,
        },
    }


def forbidden_safety_clean(details: dict[str, Any]) -> bool:
    return not any(
        value
        for key, value in details["safety"].items()
        if key != "read_only_a90ctl_commands_executed"
    )


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    input_ready = (
        details["v1859"]["pass"]
        and details["v1859"]["label"] == "transport-locator-repo-bridge-ready"
    )
    if not input_ready:
        return "input-review", "v1860-input-review", "V1859 transport locator input is missing or not ready", False
    if not forbidden_safety_clean(details):
        return "safety-review", "v1860-safety-review", "Read-only smoke claims a forbidden live action", False
    summary = details["summary"]
    if not summary["core_readonly_ok"]:
        return (
            "read-only-smoke-bridge-command-failed",
            "v1860-read-only-smoke-bridge-command-failed",
            "Core read-only status/bootstatus/selftest bridge commands did not all complete successfully",
            False,
        )
    if summary["wlfw_service69_present"] and summary["wlan0_present"]:
        return (
            "read-only-smoke-wlfw-wlan0-present",
            "v1860-read-only-smoke-wlfw-wlan0-present-host-pass",
            "Read-only bridge smoke shows WLFW service 69 and wlan0 prerequisites; scan/connect can be planned as the next reviewed gate",
            True,
        )
    if summary["wlfw_service69_present"]:
        return (
            "read-only-smoke-wlfw-present-wlan0-missing",
            "v1860-read-only-smoke-wlfw-present-wlan0-missing-host-pass",
            "Read-only bridge smoke shows WLFW service 69 evidence, but wlan0 is not present; scan/connect remain blocked",
            True,
        )
    if summary["wlan0_present"]:
        return (
            "read-only-smoke-wlan0-present-wlfw-unproven",
            "v1860-read-only-smoke-wlan0-present-wlfw-unproven-host-pass",
            "Read-only bridge smoke sees wlan0, but WLFW service 69 evidence is unproven; scan/connect require a focused prerequisite review first",
            True,
        )
    return (
        "read-only-smoke-pre-wifi-gap",
        "v1860-read-only-smoke-pre-wifi-gap-host-pass",
        "Read-only bridge commands succeed, but WLFW service 69 and wlan0 are absent/unproven; Wi-Fi HAL, scan/connect, DHCP, routes, credentials, and external ping remain blocked",
        True,
    )


def command_table(records: list[dict[str, Any]]) -> list[str]:
    rows = ["| name | command | host rc | protocol | ok |", "| --- | --- | ---: | --- | --- |"]
    for record in records:
        rows.append(
            "| {name} | `{command}` | `{host_rc}` | `{status}/{rc}` | `{ok}` |".format(
                name=record["name"],
                command=" ".join(record["command"]),
                host_rc=record["host_rc"],
                status=record["protocol_status"],
                rc=record["protocol_rc"],
                ok=command_ok(record),
            )
        )
    return rows


def render_report(result: dict[str, Any]) -> str:
    details = result["details"]
    summary = details["summary"]
    lines = [
        "# Native Init V1860 Bridge Read-Only Smoke",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: live read-only native-init bridge smoke for Wi-Fi prerequisite gating",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Input",
        "",
        f"- V1859: `{details['v1859']['decision']}` / `{details['v1859']['label']}` / pass `{details['v1859']['pass']}`",
        "",
        "## Prerequisite State",
        "",
        f"- core read-only commands ok: `{summary['core_readonly_ok']}` details `{summary['core_command_ok']}`",
        f"- successful read-only commands: `{summary['successful_command_count']}` / `{summary['total_command_count']}`",
        f"- busy read-only commands after menu activation: `{summary['busy_command_count']}`",
        f"- wifiinv `wlan_like` count: `{summary['wifiinv_wlan_like_count']}`",
        f"- wififeas decision: `{summary['wififeas_decision']}`",
        f"- WLFW service 69 present: `{summary['wlfw_service69_present']}` evidence `{summary['wlfw_service69_evidence']}`",
        f"- `wlan0` present: `{summary['wlan0_present']}` evidence `{summary['wlan0_evidence']}`",
        f"- git clean: `{details['host']['git_clean']}`",
        "",
        "## Commands",
        "",
        *command_table(details["commands"]),
        "",
        "## Safety Scope",
        "",
        "This run executed only read-only `a90ctl.py --json --allow-error` commands from the safe observation set. It did not run `version`, start a serial bridge, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
    ]
    if summary["wlfw_service69_present"] and summary["wlan0_present"]:
        lines.extend([
            "- Plan a separate constrained Wi-Fi HAL/connect gate with credential handling and rollback/cleanup.",
            "- Keep DHCP/routes/external ping as downstream checks after interface association is proven.",
        ])
    else:
        lines.extend([
            "- Keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.",
            "- Next useful unit is below this gate: continue the reviewed SDX50M/PM bridge path until WLFW service 69 and `wlan0` appear.",
        ])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    details = collect_smoke(load_json(V1859_MANIFEST))
    label, decision, reason, passed = classify(details)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "report": rel(REPORT_PATH),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("decision", "label", "pass", "reason", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
