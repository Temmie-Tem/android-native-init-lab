#!/usr/bin/env python3
"""V1861 direct read-only prerequisite check after auto-menu busy handling."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import native_wifi_bridge_readonly_smoke_v1860 as prev1860


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1861"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1861-bridge-direct-prereq"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1861_BRIDGE_DIRECT_PREREQ_2026-06-03.md"
)
V1860_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1860-bridge-readonly-smoke" / "manifest.json"
A90CTL = REPO_ROOT / "scripts" / "revalidation" / "a90ctl.py"
PAYLOAD_CHAR_LIMIT = 8000

DIRECT_READS: tuple[tuple[str, list[str], float, bool], ...] = (
    ("status-after-hide", ["status"], 10.0, True),
    ("sys-class-net", ["ls", "/sys/class/net"], 8.0, True),
    ("wlan0-stat", ["stat", "/sys/class/net/wlan0"], 8.0, True),
    ("sys-class-ieee80211", ["ls", "/sys/class/ieee80211"], 8.0, True),
    ("proc-net-wireless", ["cat", "/proc/net/wireless"], 8.0, True),
    ("proc-net-qrtr", ["cat", "/proc/net/qrtr"], 8.0, True),
    ("debug-qrtr-ns", ["cat", "/sys/kernel/debug/qrtr/qrtr-ns"], 8.0, True),
    ("wifiinv-summary", ["wifiinv", "summary"], 8.0, False),
    ("wififeas-gate", ["wififeas", "gate"], 8.0, False),
)

SAFE_READONLY_COMMAND_NAMES = {
    "status",
    "ls",
    "stat",
    "cat",
    "wifiinv",
    "wififeas",
}


def rel(path: Path) -> str:
    return prev1860.rel(path)


def load_json(path: Path) -> dict[str, Any]:
    return prev1860.load_json(path)


def clean_lines(text: str) -> list[str]:
    return prev1860.clean_lines(text)


def redact(text: str) -> str:
    return prev1860.redact(text)


def strip_protocol(text: str) -> str:
    return prev1860.strip_protocol(text)


def command_terminal(record: dict[str, Any]) -> bool:
    return (
        bool(record.get("host_available"))
        and record.get("host_rc") == 0
        and bool(record.get("parsed_json"))
        and record.get("protocol_status") != "busy"
    )


def command_ok(record: dict[str, Any]) -> bool:
    return prev1860.command_ok(record)


def find_record(records: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return prev1860.find_record(records, name)


def payload_text(records: list[dict[str, Any]], names: set[str] | None = None) -> str:
    return prev1860.payload_text(records, names)


def ensure_readonly_commands() -> None:
    unsafe = [
        command
        for _name, command, _timeout, _hide_on_busy in DIRECT_READS
        if not command or command[0] not in SAFE_READONLY_COMMAND_NAMES
    ]
    if unsafe:
        raise SystemExit(f"non-read-only command configured: {unsafe}")


def run_a90ctl(name: str, command: list[str], timeout: float, hide_on_busy: bool) -> dict[str, Any]:
    python3 = shutil.which("python3")
    if not python3:
        return {
            "name": name,
            "command": command,
            "hide_on_busy": hide_on_busy,
            "host_available": False,
            "host_rc": 127,
            "parsed_json": False,
            "protocol_rc": None,
            "protocol_status": "host-python3-missing",
            "hide_retry_triggered": False,
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
    ]
    if hide_on_busy:
        host_command.append("--hide-on-busy")
    host_command.extend(command)
    try:
        completed = subprocess.run(
            host_command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 4.0,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = redact(exc.stdout or "")
        stderr = redact(exc.stderr or "timeout")
        return {
            "name": name,
            "command": command,
            "hide_on_busy": hide_on_busy,
            "host_available": True,
            "host_rc": 124,
            "parsed_json": False,
            "protocol_rc": None,
            "protocol_status": "host-timeout",
            "hide_retry_triggered": "sending hide" in stderr,
            "payload": strip_protocol(stdout)[:PAYLOAD_CHAR_LIMIT],
            "payload_lines": prev1860.truncated_lines(strip_protocol(stdout)),
            "stderr_lines": prev1860.truncated_lines(stderr, 12),
        }

    stderr = redact(completed.stderr)
    parsed: dict[str, Any] | None = None
    try:
        loaded = json.loads(completed.stdout)
        if isinstance(loaded, dict):
            parsed = loaded
    except json.JSONDecodeError:
        parsed = None
    text = str(parsed.get("text", "")) if parsed else redact(completed.stdout)
    payload = strip_protocol(redact(text))
    if len(payload) > PAYLOAD_CHAR_LIMIT:
        payload = payload[:PAYLOAD_CHAR_LIMIT] + "\n[truncated]\n"
    end = parsed.get("end", {}) if parsed else {}
    return {
        "name": name,
        "command": command,
        "hide_on_busy": hide_on_busy,
        "host_available": True,
        "host_rc": completed.returncode,
        "parsed_json": parsed is not None,
        "protocol_rc": parsed.get("rc") if parsed else None,
        "protocol_status": parsed.get("status") if parsed else "json-parse-failed",
        "begin": parsed.get("begin", {}) if parsed else {},
        "end": end if isinstance(end, dict) else {},
        "hide_retry_triggered": "sending hide" in stderr,
        "payload": payload,
        "payload_lines": prev1860.truncated_lines(payload),
        "stderr_lines": prev1860.truncated_lines(stderr, 12),
    }


def token_lines(text: str, token: str) -> list[str]:
    pattern = re.compile(rf"(^|[^A-Za-z0-9_]){re.escape(token)}([^A-Za-z0-9_]|$)")
    return [line for line in clean_lines(text) if pattern.search(line)]


def wlan0_state(records: list[dict[str, Any]]) -> dict[str, Any]:
    stat_record = find_record(records, "wlan0-stat")
    text = payload_text(records, {"sys-class-net", "wlan0-stat", "proc-net-wireless", "wifiinv-summary"})
    lines = token_lines(text, "wlan0")
    no_such = any("No such file" in line or "No such file or directory" in line for line in clean_lines(text))
    wifiinv_count = prev1860.wifiinv_wlan_like_count(records)
    present = command_ok(stat_record) or (bool(lines) and not no_such) or (wifiinv_count is not None and wifiinv_count > 0)
    absent_confirmed = (
        command_terminal(find_record(records, "sys-class-net"))
        and command_terminal(stat_record)
        and not present
    ) or (wifiinv_count == 0 and not present)
    return {
        "present": bool(present),
        "absent_confirmed": bool(absent_confirmed),
        "evidence": lines[:12],
        "wifiinv_wlan_like_count": wifiinv_count,
        "stat_protocol_status": stat_record.get("protocol_status", ""),
        "stat_protocol_rc": stat_record.get("protocol_rc"),
    }


def wlfw_service69_state(records: list[dict[str, Any]]) -> dict[str, Any]:
    text = payload_text(records, {"proc-net-qrtr", "debug-qrtr-ns", "wifiinv-summary", "wififeas-gate"})
    positive_patterns = (
        re.compile(r"\bwlfw\b.*\b(service\s*)?69\b.*\b(present|seen|found|online|up|published|true|1)\b", re.I),
        re.compile(r"\b(service\s*)?69\b.*\bwlfw\b.*\b(present|seen|found|online|up|published|true|1)\b", re.I),
        re.compile(r"\bwlfw[_ .-]*service[_ .-]*69[_ .-]*(seen|present|progress)\s*[:=]\s*(1|true|yes)", re.I),
        re.compile(r"\blower[_ .-]*service69[_ .-]*progress\s*[:=]\s*(1|true|yes)", re.I),
    )
    negative_re = re.compile(r"\b(absent|missing|not\s+found|false|no|none)\b", re.I)
    positive_lines = [
        line
        for line in clean_lines(text)
        if any(pattern.search(line) for pattern in positive_patterns) and not negative_re.search(line)
    ]
    direct_qrtr_terminal = command_terminal(find_record(records, "proc-net-qrtr")) or command_terminal(find_record(records, "debug-qrtr-ns"))
    return {
        "present": bool(positive_lines),
        "absent_or_unproven": not bool(positive_lines),
        "direct_qrtr_terminal": direct_qrtr_terminal,
        "evidence": positive_lines[:12],
    }


def collect(v1860: dict[str, Any]) -> dict[str, Any]:
    ensure_readonly_commands()
    git_status = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    records = [run_a90ctl(name, command, timeout, hide_on_busy) for name, command, timeout, hide_on_busy in DIRECT_READS]
    wlan0 = wlan0_state(records)
    wlfw69 = wlfw_service69_state(records)
    direct_busy_remaining = [record["name"] for record in records if record.get("protocol_status") == "busy"]
    return {
        "v1860": {
            "path": rel(V1860_MANIFEST),
            "decision": v1860.get("decision", ""),
            "label": v1860.get("label", ""),
            "pass": bool(v1860.get("pass")),
        },
        "host": {
            "git_clean": git_status.returncode == 0 and git_status.stdout == "",
            "git_status_lines": clean_lines(git_status.stdout)[:20],
        },
        "commands": records,
        "summary": {
            "terminal_direct_read_count": sum(1 for record in records if command_terminal(record)),
            "ok_direct_read_count": sum(1 for record in records if command_ok(record)),
            "total_command_count": len(records),
            "hide_retry_count": sum(1 for record in records if record.get("hide_retry_triggered")),
            "busy_remaining": direct_busy_remaining,
            "wlan0": wlan0,
            "wlfw_service69": wlfw69,
            "wififeas_decision": prev1860.wififeas_decision(records),
        },
        "safety": {
            "read_only_a90ctl_commands_executed": True,
            "ui_hide_on_busy_executed": any(record.get("hide_retry_triggered") for record in records),
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
    allowed = {"read_only_a90ctl_commands_executed", "ui_hide_on_busy_executed"}
    return not any(value for key, value in details["safety"].items() if key not in allowed)


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    input_ready = (
        details["v1860"]["pass"]
        and details["v1860"]["label"] == "read-only-smoke-pre-wifi-gap"
    )
    if not input_ready:
        return "input-review", "v1861-input-review", "V1860 read-only smoke input is missing or not at the pre-Wi-Fi gap", False
    if not forbidden_safety_clean(details):
        return "safety-review", "v1861-safety-review", "Direct prerequisite check claims a forbidden action", False
    summary = details["summary"]
    if summary["busy_remaining"]:
        return (
            "direct-prereq-busy-remaining",
            "v1861-direct-prereq-busy-remaining",
            f"Auto-menu busy remained after hide-on-busy for {summary['busy_remaining']}",
            False,
        )
    wlan0_present = bool(summary["wlan0"]["present"])
    wlfw_present = bool(summary["wlfw_service69"]["present"])
    if wlfw_present and wlan0_present:
        return (
            "direct-prereq-wlfw-wlan0-present",
            "v1861-direct-prereq-wlfw-wlan0-present-host-pass",
            "Direct read-only evidence shows WLFW service 69 and wlan0; a separate reviewed connect gate is now justified",
            True,
        )
    if wlfw_present:
        return (
            "direct-prereq-wlfw-present-wlan0-missing",
            "v1861-direct-prereq-wlfw-present-wlan0-missing-host-pass",
            "Direct read-only evidence shows WLFW service 69 but wlan0 remains absent; Wi-Fi connect remains blocked",
            True,
        )
    if wlan0_present:
        return (
            "direct-prereq-wlan0-present-wlfw-unproven",
            "v1861-direct-prereq-wlan0-present-wlfw-unproven-host-pass",
            "Direct read-only evidence sees wlan0 but WLFW service 69 remains unproven; connect requires a focused prerequisite review first",
            True,
        )
    return (
        "direct-prereq-pre-wifi-gap-confirmed",
        "v1861-direct-prereq-pre-wifi-gap-confirmed-host-pass",
        "Auto-menu busy was removed for direct read-only checks, and WLFW service 69 plus wlan0 remain absent/unproven; connect/ping remain blocked below the prerequisite gate",
        True,
    )


def command_table(records: list[dict[str, Any]]) -> list[str]:
    rows = ["| name | command | hide | host rc | protocol | terminal |", "| --- | --- | --- | ---: | --- | --- |"]
    for record in records:
        rows.append(
            "| {name} | `{command}` | `{hide}` | `{host_rc}` | `{status}/{rc}` | `{terminal}` |".format(
                name=record["name"],
                command=" ".join(record["command"]),
                hide=record["hide_retry_triggered"],
                host_rc=record["host_rc"],
                status=record["protocol_status"],
                rc=record["protocol_rc"],
                terminal=command_terminal(record),
            )
        )
    return rows


def render_report(result: dict[str, Any]) -> str:
    details = result["details"]
    summary = details["summary"]
    lines = [
        "# Native Init V1861 Bridge Direct Prerequisite Check",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: live read-only direct prerequisite check with auto-menu busy handling",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Input",
        "",
        f"- V1860: `{details['v1860']['decision']}` / `{details['v1860']['label']}` / pass `{details['v1860']['pass']}`",
        "",
        "## Direct Prerequisites",
        "",
        f"- terminal direct reads: `{summary['terminal_direct_read_count']}` / `{summary['total_command_count']}`",
        f"- ok direct reads: `{summary['ok_direct_read_count']}` / `{summary['total_command_count']}`",
        f"- hide retry count: `{summary['hide_retry_count']}`",
        f"- busy remaining: `{summary['busy_remaining']}`",
        f"- wififeas decision: `{summary['wififeas_decision']}`",
        f"- WLFW service 69 present: `{summary['wlfw_service69']['present']}` evidence `{summary['wlfw_service69']['evidence']}` direct_qrtr_terminal `{summary['wlfw_service69']['direct_qrtr_terminal']}`",
        f"- `wlan0` present: `{summary['wlan0']['present']}` absent_confirmed `{summary['wlan0']['absent_confirmed']}` evidence `{summary['wlan0']['evidence']}` wifiinv_wlan_like `{summary['wlan0']['wifiinv_wlan_like_count']}`",
        f"- git clean: `{details['host']['git_clean']}`",
        "",
        "## Commands",
        "",
        *command_table(details["commands"]),
        "",
        "## Safety Scope",
        "",
        "This run executed only read-only `a90ctl.py --json --allow-error` observations. `--hide-on-busy` was allowed only to dismiss the native auto menu before retrying the same read-only command. It did not run `version`, start a serial bridge, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
    ]
    if summary["wlfw_service69"]["present"] and summary["wlan0"]["present"]:
        lines.append("- Prepare a separate constrained Wi-Fi connect gate with credential redaction, timeout, cleanup, DHCP/route evidence, and external ping only after association.")
    else:
        lines.extend([
            "- Keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.",
            "- Continue the reviewed SDX50M/PM bridge path; the next useful work must make WLFW service 69 or `wlan0` appear, not retry connect.",
        ])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    details = collect(load_json(V1860_MANIFEST))
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
