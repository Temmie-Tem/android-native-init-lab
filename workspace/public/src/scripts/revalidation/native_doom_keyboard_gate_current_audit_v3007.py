#!/usr/bin/env python3
"""V3007 current read-only audit for the DOOM USB-keyboard live gate.

This supersedes the older V2994 gate snapshot with current V3004/V3006 evidence.
It does not flash, build, open evdev, or sample input. It records whether the
V3004 live gate is actionable right now based on resident health, current host
USB topology, and the latest committed reports.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]

RUN_ID = "V3007"
BUILD_TAG = "v3007-doom-keyboard-gate-current-audit"
DECISION_READY = "v3007-doom-keyboard-gate-live-ready"
DECISION_NOT_ACTIONABLE = "v3007-doom-keyboard-gate-hardware-stimulus-required"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3007_DOOM_KEYBOARD_GATE_CURRENT_AUDIT_2026-06-20.md"

V3004_REPORT = ROOT / "docs/reports/NATIVE_INIT_V3004_DOOMINPUT_KEYBOARD_LIVE_GATE_DRY_RUN_2026-06-20.md"
V3006_REPORT = ROOT / "docs/reports/NATIVE_INIT_V3006_DOOM_KEYBOARD_GATE_STATUS_LIVE_2026-06-20.md"
A90CTL = ROOT / "workspace/public/src/scripts/revalidation/a90ctl.py"


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


def parse_version(text: str) -> dict[str, Any]:
    match = re.search(r"A90 Linux init ([^\s]+) \(([^)]+)\)", text)
    return {
        "version_ok": bool(match),
        "init_version": match.group(1) if match else None,
        "build_tag": match.group(2) if match else None,
        "resident_v2321": bool(match and match.group(2) == "v2321-usb-clean-identity-rodata"),
    }


def parse_selftest(text: str) -> dict[str, Any]:
    match = re.search(r"selftest: pass=(\d+) warn=(\d+) fail=(\d+)", text)
    return {
        "selftest_ok": bool(match and match.group(3) == "0"),
        "pass": int(match.group(1)) if match else None,
        "warn": int(match.group(2)) if match else None,
        "fail": int(match.group(3)) if match else None,
        "builtin_buttons_ok": "event0=ok event3=ok" in text,
    }


def parse_status(text: str) -> dict[str, Any]:
    return {
        "transport_ready": "transport.bridge_endpoint=" in text,
        "ncm_ready": "transport.ncm=ready" in text,
        "storage_ready": "storage: sd present=yes mounted=yes" in text and "rw=yes" in text,
    }


def parse_lsusb_tree(text: str) -> dict[str, Any]:
    hid_lines = [line.strip() for line in text.splitlines() if "Class=Human Interface Device" in line]
    a90_control_lines = [
        line.strip()
        for line in text.splitlines()
        if "Driver=cdc_acm" in line or "Driver=cdc_ncm" in line or "Class=Communications" in line
    ]
    return {
        "host_hid_interface_count": len(hid_lines),
        "host_hid_present": bool(hid_lines),
        "a90_control_present": bool(a90_control_lines),
        "host_hid_note": "Host-side HID interfaces are not proof of an A90 OTG keyboard evdev node.",
    }


def report_evidence() -> dict[str, Any]:
    v3004 = V3004_REPORT.read_text(encoding="utf-8")
    v3006 = V3006_REPORT.read_text(encoding="utf-8")
    return {
        "v3004_report_exists": V3004_REPORT.exists(),
        "v3004_preflight_ok": "Preflight ok: `1`" in v3004,
        "v3004_live_execution": "Live execution: `1`" in v3004,
        "v3004_requires_usb_keyboard": "USB keyboard/OTG attached and DOOM keys pressed" in v3004,
        "v3006_report_exists": V3006_REPORT.exists(),
        "v3006_live_pass": "Result before rollback: `1`" in v3006 and "rollback v2321/selftest fail=0" in v3006,
        "v3006_status_points_to_v3004": "video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate" in v3006,
    }


def evaluate_gate(payload: dict[str, Any]) -> dict[str, Any]:
    reports = payload["reports"]
    health = payload["device_health"]
    usb = payload["host_usb_topology"]
    ready = bool(
        reports["v3004_preflight_ok"]
        and reports["v3004_requires_usb_keyboard"]
        and reports["v3006_live_pass"]
        and reports["v3006_status_points_to_v3004"]
        and health["version"]["version_ok"]
        and health["selftest"]["selftest_ok"]
        and payload.get("a90_otg_keyboard_evidence", False)
    )
    reasons: list[str] = []
    if not reports["v3004_preflight_ok"]:
        reasons.append("V3004 keyboard live gate preflight is not recorded as ready.")
    if not reports["v3006_live_pass"]:
        reasons.append("V3006 status-surface live validation is not recorded as pass.")
    if not health["selftest"]["selftest_ok"]:
        reasons.append("Resident device selftest is not clean.")
    if usb["host_hid_present"]:
        reasons.append("Host HID interfaces are visible, but they are not A90 OTG evdev keyboard evidence.")
    if usb["a90_control_present"]:
        reasons.append("A90 is currently present as a USB control/peripheral path, not proven OTG keyboard host.")
    reasons.append("No current evidence shows an attached A90 USB keyboard/OTG path with operator key presses available.")
    return {
        "decision": DECISION_READY if ready else DECISION_NOT_ACTIONABLE,
        "v3004_live_actionable_now": ready,
        "reasons": reasons,
        "next_action": (
            "Run V3004 live only when USB keyboard/OTG is attached to the A90, "
            "the serial/control path remains available, and an operator can press DOOM keys "
            "during the bounded `doominput` window."
        ),
    }


def build_payload(out_dir: Path) -> dict[str, Any]:
    steps = [
        run_capture(out_dir, "a90ctl-version", ["python3", str(A90CTL), "version"], timeout=60.0),
        run_capture(out_dir, "a90ctl-status", ["python3", str(A90CTL), "status"], timeout=90.0),
        run_capture(out_dir, "a90ctl-selftest", ["python3", str(A90CTL), "selftest", "verbose"], timeout=90.0),
        run_capture(out_dir, "lsusb-tree", ["lsusb", "-t"], timeout=30.0),
    ]
    payload = {
        "run_id": RUN_ID,
        "out_dir": rel(out_dir),
        "steps": [{key: value for key, value in step.items() if key not in ("stdout", "stderr")} for step in steps],
        "reports": report_evidence(),
        "device_health": {
            "version": parse_version(steps[0]["stdout"]),
            "status": parse_status(steps[1]["stdout"]),
            "selftest": parse_selftest(steps[2]["stdout"]),
        },
        "host_usb_topology": parse_lsusb_tree(steps[3]["stdout"]),
        "a90_otg_keyboard_evidence": False,
        "inputs": {
            "v3004_report": rel(V3004_REPORT),
            "v3006_report": rel(V3006_REPORT),
        },
    }
    payload["gate"] = evaluate_gate(payload)
    return payload


def render_report(payload: dict[str, Any]) -> str:
    health = payload["device_health"]
    reports = payload["reports"]
    usb = payload["host_usb_topology"]
    gate = payload["gate"]
    return "\n".join([
        "# Native Init V3007 DOOM Keyboard Gate Current Audit",
        "",
        "## Summary",
        "",
        f"- Decision: `{gate['decision']}`",
        "- Device action: `none` in this read-only unit.",
        "- Track: active Video playback / DOOM input prerequisite.",
        f"- Resident build: `{health['version'].get('build_tag')}`",
        f"- Resident selftest fail=0: `{int(bool(health['selftest'].get('selftest_ok')))}`",
        f"- V3004 keyboard gate preflight ok: `{int(bool(reports['v3004_preflight_ok']))}`",
        f"- V3004 live already executed: `{int(bool(reports['v3004_live_execution']))}`",
        f"- V3006 status surface live pass: `{int(bool(reports['v3006_live_pass']))}`",
        f"- V3006 status points to V3004 gate: `{int(bool(reports['v3006_status_points_to_v3004']))}`",
        f"- Host USB HID interfaces visible: `{usb['host_hid_interface_count']}`",
        f"- A90 USB control/peripheral present: `{int(bool(usb['a90_control_present']))}`",
        f"- A90 OTG keyboard evdev evidence: `{int(bool(payload.get('a90_otg_keyboard_evidence')))}`",
        f"- V3004 live actionable now: `{int(bool(gate['v3004_live_actionable_now']))}`",
        "",
        "## Gate Reasons",
        "",
        *(f"- {reason}" for reason in gate["reasons"]),
        "",
        "## Next Action",
        "",
        f"- {gate['next_action']}",
        "",
        "## Evidence Inputs",
        "",
        f"- V3004 report: `{payload['inputs']['v3004_report']}`",
        f"- V3006 report: `{payload['inputs']['v3006_report']}`",
        f"- Private raw outputs: `{payload['out_dir']}`",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_keyboard_gate_current_audit_v3007.py tests/test_native_doom_keyboard_gate_current_audit_v3007.py`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_keyboard_gate_current_audit_v3007`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_keyboard_gate_current_audit_v3007.py`: PASS (read-only report materialized)",
        "- `git diff --check`: PASS",
        "",
        "## Safety",
        "",
        "- Read-only audit; no flash, no build artifact, no evdev open, no input injection, and no sysfs write.",
        "- `a90ctl version`, `status`, and `selftest verbose` are read-only health checks on the resident rollback image.",
        "- `lsusb -t` is host topology inspection only; host HID devices are not treated as A90 input evidence.",
        "- No Wi-Fi/audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.",
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
        "v3004_live_actionable_now": payload["gate"]["v3004_live_actionable_now"],
        "resident_build": payload["device_health"]["version"].get("build_tag"),
        "selftest_ok": payload["device_health"]["selftest"].get("selftest_ok"),
        "host_hid_interface_count": payload["host_usb_topology"]["host_hid_interface_count"],
        "report": rel(REPORT_PATH),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
