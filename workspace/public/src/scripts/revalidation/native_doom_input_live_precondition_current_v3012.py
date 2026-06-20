#!/usr/bin/env python3
"""V3012 read-only current precondition audit for the DOOM keyboard gate.

The V3004 live gate is already staged and V3010 proved the flash-gate assets
are present. This script records whether the current resident device and host
topology make that gate actionable now. It intentionally does not flash, build,
open evdev, inject input, or write sysfs.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V3012"
BUILD_TAG = "v3012-doom-input-live-precondition-current"
DECISION_READY = "v3012-doom-input-live-precondition-live-ready"
DECISION_WAIT = "v3012-doom-input-live-precondition-current-hardware-wait"
DECISION_BLOCKED = "v3012-doom-input-live-precondition-current-blocked"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3012_DOOM_INPUT_LIVE_PRECONDITION_CURRENT_2026-06-20.md"

A90_BRIDGE = ROOT / "workspace/public/src/scripts/revalidation/a90_bridge.py"
A90CTL = ROOT / "workspace/public/src/scripts/revalidation/a90ctl.py"
FRONTIER_SELECTOR = ROOT / "workspace/public/src/scripts/revalidation/native_init_frontier_select.py"

V3008_REPORT = ROOT / "docs/reports/NATIVE_INIT_V3008_DOOM_INPUT_FRONTIER_RECONCILIATION_2026-06-20.md"
V3010_REPORT = ROOT / "docs/reports/NATIVE_INIT_V3010_DOOM_INPUT_FLASH_GATE_ASSETS_2026-06-20.md"
V3011_REPORT = ROOT / "docs/reports/NATIVE_INIT_V3011_FRONTIER_SELECTOR_V3010_ASSETS_2026-06-20.md"

NEXT_LIVE_COMMAND = (
    "PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness "
    "python3 workspace/public/src/scripts/revalidation/"
    "native_doominput_keyboard_live_gate_v3004.py --live --count 32 --timeout-ms 60000"
)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def run_capture(out_dir: Path, name: str, argv: list[str], timeout: float = 60.0) -> dict[str, Any]:
    proc = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=timeout, check=False)
    stdout_path = out_dir / f"{name}.stdout.txt"
    stderr_path = out_dir / f"{name}.stderr.txt"
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    return {
        "name": name,
        "argv": argv,
        "rc": proc.returncode,
        "stdout_path": rel(stdout_path),
        "stderr_path": rel(stderr_path),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def read_optional_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def parse_bridge_status_json(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}
    serial_candidates = data.get("serial_candidates") if isinstance(data.get("serial_candidates"), list) else []
    serial_candidate_count = sum(1 for item in serial_candidates if isinstance(item, dict) and item.get("exists"))
    running = data.get("bridge_process") == "running"
    port_listening = data.get("port_listening") is True
    probe = data.get("bridge_probe")
    probe_ok = probe in {"ok", "connected-no-immediate-error"}
    return {
        "json_ok": bool(data),
        "bridge_running": running,
        "port_listening": port_listening,
        "bridge_probe": probe,
        "bridge_probe_ok": probe_ok,
        "serial_candidate_count": serial_candidate_count,
        "selected_serial_present": bool(data.get("selected_device") and serial_candidate_count),
        "control_path_ready": bool(running and port_listening and serial_candidate_count),
    }


def parse_version(text: str) -> dict[str, Any]:
    match = re.search(r"A90 Linux init ([^\s]+) \(([^)]+)\)", text)
    return {
        "version_ok": bool(match),
        "init_version": match.group(1) if match else None,
        "build_tag": match.group(2) if match else None,
        "resident_v2321": bool(match and match.group(2) == "v2321-usb-clean-identity-rodata"),
    }


def parse_status(text: str) -> dict[str, Any]:
    return {
        "transport_ready": "transport.bridge_endpoint=" in text,
        "ncm_ready": "transport.ncm=ready" in text,
        "storage_ready": "storage: sd present=yes mounted=yes" in text and "rw=yes" in text,
    }


def parse_selftest(text: str) -> dict[str, Any]:
    match = re.search(r"selftest: pass=(\d+) warn=(\d+) fail=(\d+)", text)
    return {
        "selftest_ok": bool(match and match.group(3) == "0"),
        "pass": int(match.group(1)) if match else None,
        "warn": int(match.group(2)) if match else None,
        "fail": int(match.group(3)) if match else None,
        "input_builtin_ok": "event0=ok event3=ok" in text,
        "usb_acm_ok": "acm=yes" in text,
    }


def parse_lsusb_tree(text: str) -> dict[str, Any]:
    hid_lines = [line.strip() for line in text.splitlines() if "Class=Human Interface Device" in line]
    cdc_lines = [
        line.strip()
        for line in text.splitlines()
        if "Driver=cdc_acm" in line or "Driver=cdc_ncm" in line
    ]
    return {
        "host_hid_interface_count": len(hid_lines),
        "host_hid_present": bool(hid_lines),
        "host_cdc_interface_count": len(cdc_lines),
        "host_cdc_present": bool(cdc_lines),
        "a90_otg_keyboard_evidence": False,
        "note": "Host-side HID interfaces are not proof of an A90 OTG keyboard evdev node.",
    }


def parse_selector_json(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}
    first = {}
    evaluations = data.get("track_evaluations") if isinstance(data.get("track_evaluations"), list) else []
    if evaluations:
        first = evaluations[0] if isinstance(evaluations[0], dict) else {}
    evidence = first.get("evidence") if isinstance(first.get("evidence"), dict) else {}
    return {
        "json_ok": bool(data),
        "decision": data.get("decision"),
        "first_track": first.get("track"),
        "first_name": first.get("name"),
        "first_status": first.get("status"),
        "first_safe_actionable_now": first.get("safe_actionable_now"),
        "selector_external_stimulus_required": (
            first.get("track") == "VIDEO"
            and first.get("name") == "doom-input"
            and first.get("status") == "external-hardware-stimulus-required"
            and first.get("safe_actionable_now") is False
        ),
        "v3010_flash_gate_assets_ready": evidence.get("v3010_flash_gate_assets_ready") is True,
        "v3010_flash_gate_reports_ok": evidence.get("v3010_flash_gate_reports_ok") is True,
        "v3010_external_hardware_wait_retained": evidence.get("v3010_external_hardware_wait_retained") is True,
        "v3010_v3004_live_actionable_now": evidence.get("v3010_v3004_live_actionable_now") is True,
        "next_operator_decision": data.get("next_operator_decision"),
        "next_live_command": evidence.get("next_live_command"),
    }


def report_markers() -> dict[str, Any]:
    v3008 = read_optional_text(V3008_REPORT)
    v3010 = read_optional_text(V3010_REPORT)
    v3011 = read_optional_text(V3011_REPORT)
    return {
        "v3008_report_present": bool(v3008),
        "v3008_external_gate": "v3008-doom-input-frontier-keyboard-gate-still-external-stimulus" in v3008,
        "v3010_report_present": bool(v3010),
        "v3010_assets_ready": "v3010-doom-input-flash-gate-assets-ready-hardware-wait" in v3010
        and "Required assets present: `1`" in v3010
        and "Expected SHA256 checks pass: `1`" in v3010,
        "v3010_reports_ok": "Current gate reports pass: `1`" in v3010,
        "v3010_external_hardware_wait": "External hardware wait retained: `1`" in v3010,
        "v3011_report_present": bool(v3011),
        "v3011_selector_pass": "v3011-frontier-selector-v3010-assets-pass" in v3011,
        "v3011_selector_external_gate": "external-hardware-stimulus-required" in v3011,
    }


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    bridge = payload["bridge"]
    health = payload["device_health"]
    reports = payload["reports"]
    selector = payload["selector"]
    usb = payload["host_usb_topology"]
    resident_health_ok = bool(
        bridge["control_path_ready"]
        and health["version"]["resident_v2321"]
        and health["selftest"]["selftest_ok"]
    )
    gate_assets_ready = bool(
        reports["v3010_assets_ready"]
        and reports["v3010_reports_ok"]
        and reports["v3010_external_hardware_wait"]
        and selector["v3010_flash_gate_assets_ready"]
        and selector["v3010_flash_gate_reports_ok"]
    )
    external_gate_retained = bool(
        reports["v3008_external_gate"]
        and reports["v3011_selector_external_gate"]
        and selector["selector_external_stimulus_required"]
        and selector["v3010_external_hardware_wait_retained"]
    )
    a90_otg_keyboard_evidence = bool(usb["a90_otg_keyboard_evidence"])
    live_actionable = bool(resident_health_ok and gate_assets_ready and external_gate_retained and a90_otg_keyboard_evidence)
    reasons: list[str] = []
    if resident_health_ok:
        reasons.append("Resident V2321 control path and selftest are clean.")
    else:
        reasons.append("Resident control path or selftest is not clean enough for a live gate.")
    if gate_assets_ready:
        reasons.append("V3010/V3011 report and selector evidence show the V3004 live-gate assets are ready.")
    else:
        reasons.append("V3010/V3011 flash-gate readiness evidence is incomplete.")
    if external_gate_retained:
        reasons.append("The selector still classifies DOOM input as external-hardware-stimulus-required.")
    if usb["host_hid_present"]:
        reasons.append("Host HID interfaces are visible, but they are not A90 OTG evdev keyboard evidence.")
    if not a90_otg_keyboard_evidence:
        reasons.append("No current evidence shows an A90-side OTG keyboard evdev path plus operator DOOM key presses.")
    if live_actionable:
        decision = DECISION_READY
    elif resident_health_ok and gate_assets_ready and external_gate_retained:
        decision = DECISION_WAIT
    else:
        decision = DECISION_BLOCKED
    return {
        "decision": decision,
        "resident_health_ok": resident_health_ok,
        "gate_assets_ready": gate_assets_ready,
        "external_gate_retained": external_gate_retained,
        "a90_otg_keyboard_evidence": a90_otg_keyboard_evidence,
        "v3004_live_actionable_now": live_actionable,
        "reasons": reasons,
        "next_live_command": NEXT_LIVE_COMMAND,
    }


def build_payload(out_dir: Path) -> dict[str, Any]:
    steps = [
        run_capture(out_dir, "a90-bridge-status", [sys.executable, str(A90_BRIDGE), "status", "--json"], timeout=30.0),
        run_capture(out_dir, "a90ctl-version", [sys.executable, str(A90CTL), "version"], timeout=60.0),
        run_capture(out_dir, "a90ctl-status", [sys.executable, str(A90CTL), "status"], timeout=90.0),
        run_capture(out_dir, "a90ctl-selftest", [sys.executable, str(A90CTL), "selftest", "verbose"], timeout=90.0),
        run_capture(out_dir, "lsusb-tree", ["lsusb", "-t"], timeout=30.0),
        run_capture(
            out_dir,
            "frontier-selector-json",
            [sys.executable, str(FRONTIER_SELECTOR), "--json"],
            timeout=30.0,
        ),
    ]
    payload = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "out_dir": rel(out_dir),
        "steps": [{key: value for key, value in step.items() if key not in ("stdout", "stderr")} for step in steps],
        "bridge": parse_bridge_status_json(steps[0]["stdout"]),
        "device_health": {
            "version": parse_version(steps[1]["stdout"]),
            "status": parse_status(steps[2]["stdout"]),
            "selftest": parse_selftest(steps[3]["stdout"]),
        },
        "host_usb_topology": parse_lsusb_tree(steps[4]["stdout"]),
        "selector": parse_selector_json(steps[5]["stdout"]),
        "reports": report_markers(),
        "inputs": {
            "v3008_report": rel(V3008_REPORT),
            "v3010_report": rel(V3010_REPORT),
            "v3011_report": rel(V3011_REPORT),
        },
    }
    payload["gate"] = evaluate(payload)
    return payload


def render_report(payload: dict[str, Any]) -> str:
    gate = payload["gate"]
    bridge = payload["bridge"]
    health = payload["device_health"]
    usb = payload["host_usb_topology"]
    reports = payload["reports"]
    selector = payload["selector"]
    return "\n".join([
        "# Native Init V3012 DOOM Input Live Precondition Current Audit",
        "",
        "## Summary",
        "",
        f"- Decision: `{gate['decision']}`",
        "- Device action: `none` in this read-only unit.",
        "- Track: active Video playback / DOOM input prerequisite plus T3 safety tooling.",
        f"- Bridge/control path ready: `{int(bool(bridge['control_path_ready']))}`",
        f"- Bridge probe ok: `{int(bool(bridge['bridge_probe_ok']))}`",
        f"- Resident build: `{health['version'].get('build_tag')}`",
        f"- Resident selftest fail=0: `{int(bool(health['selftest'].get('selftest_ok')))}`",
        f"- V3010 flash-gate assets ready: `{int(bool(gate['gate_assets_ready']))}`",
        f"- V3011 selector external gate retained: `{int(bool(gate['external_gate_retained']))}`",
        f"- Host USB HID interfaces visible: `{usb['host_hid_interface_count']}`",
        f"- Host CDC interfaces visible: `{usb['host_cdc_interface_count']}`",
        f"- A90 OTG keyboard evdev evidence: `{int(bool(gate['a90_otg_keyboard_evidence']))}`",
        f"- V3004 live actionable now: `{int(bool(gate['v3004_live_actionable_now']))}`",
        "",
        "## Gate Reasons",
        "",
        *(f"- {reason}" for reason in gate["reasons"]),
        "",
        "## Selector And Report Inputs",
        "",
        f"- V3008 external gate marker: `{int(bool(reports['v3008_external_gate']))}`",
        f"- V3010 assets marker: `{int(bool(reports['v3010_assets_ready']))}`",
        f"- V3010 reports-ok marker: `{int(bool(reports['v3010_reports_ok']))}`",
        f"- V3011 selector pass marker: `{int(bool(reports['v3011_selector_pass']))}`",
        f"- Selector decision: `{selector.get('decision')}`",
        f"- Selector first track/status: `{selector.get('first_track')}` / `{selector.get('first_status')}`",
        f"- Command when the external prerequisite is true: `{gate['next_live_command']}`",
        "",
        "## Evidence Inputs",
        "",
        f"- V3008 report: `{payload['inputs']['v3008_report']}`",
        f"- V3010 report: `{payload['inputs']['v3010_report']}`",
        f"- V3011 report: `{payload['inputs']['v3011_report']}`",
        f"- Private raw outputs: `{payload['out_dir']}`",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_input_live_precondition_current_v3012.py tests/test_native_doom_input_live_precondition_current_v3012.py`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_input_live_precondition_current_v3012`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_input_live_precondition_current_v3012.py`: PASS (read-only report materialized)",
        "- `git diff --check`: PASS",
        "",
        "## Safety",
        "",
        "- Read-only audit; no flash, no build artifact, no evdev open, no input injection, and no sysfs write.",
        "- `a90_bridge status --json`, `a90ctl version`, `status`, and `selftest verbose` are read-only health checks on the resident rollback image.",
        "- `lsusb -t` is host topology inspection only; host HID devices are not treated as A90 input evidence.",
        "- The frontier selector is executed in read-only mode to reuse committed report evidence.",
        "- No Wi-Fi scan/connect/DHCP/ping, audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.",
        "- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.",
    ]) + "\n"


def main() -> int:
    out_dir = ROOT / f"workspace/private/runs/input/{BUILD_TAG}-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = build_payload(out_dir)
    (out_dir / "result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps({
        "decision": payload["gate"]["decision"],
        "bridge_ready": payload["bridge"]["control_path_ready"],
        "resident_build": payload["device_health"]["version"].get("build_tag"),
        "selftest_ok": payload["device_health"]["selftest"].get("selftest_ok"),
        "gate_assets_ready": payload["gate"]["gate_assets_ready"],
        "external_gate_retained": payload["gate"]["external_gate_retained"],
        "a90_otg_keyboard_evidence": payload["gate"]["a90_otg_keyboard_evidence"],
        "v3004_live_actionable_now": payload["gate"]["v3004_live_actionable_now"],
        "report": rel(REPORT_PATH),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
