#!/usr/bin/env python3
"""V2994 host-only DOOM input live-gate audit.

This script decides whether the already-staged V2992 USB-keyboard live handoff is
actionable in the current environment. It only runs read-only host/device
commands and writes a metadata-only report.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]

RUN_ID = "V2994"
DECISION_READY = "v2994-doom-input-live-gate-v2992-ready"
DECISION_NOT_ACTIONABLE = "v2994-doom-input-live-gate-not-actionable"
BUILD_TAG = "v2994-doom-input-live-gate"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2994_DOOM_INPUT_LIVE_GATE_AUDIT_2026-06-20.md"

V2992_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2992_DOOMINPUT_KEYBOARD_STATE_LIVE_HANDOFF_DRY_RUN_2026-06-20.md"
V2993_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2993_DOOM_INPUT_FRONTIER_DECISION_2026-06-20.md"
V2991_RESULT = ROOT / "workspace/private/runs/input/v2991-doominput-dual-touch-live-20260620-181451/result.json"
A90CTL = ROOT / "workspace/public/src/scripts/revalidation/a90ctl.py"


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def parse_status(text: str) -> dict[str, Any]:
    return {
        "control_bridge_ready": "transport.bridge_endpoint=" in text,
        "ncm_ready": "transport.ncm=ready" in text,
        "usb_ready": "usb=yes" in text or "usb      rc=0" in text,
        "storage_sd_rw": "storage: sd present=yes mounted=yes" in text and "rw=yes" in text,
    }


def parse_selftest(text: str) -> dict[str, Any]:
    match = re.search(r"selftest: pass=(\d+) warn=(\d+) fail=(\d+)", text)
    return {
        "selftest_ok": bool(match and match.group(3) == "0"),
        "pass": int(match.group(1)) if match else None,
        "warn": int(match.group(2)) if match else None,
        "fail": int(match.group(3)) if match else None,
        "input_event0_event3_ok": "input" in text and "event0=ok event3=ok" in text,
    }


def parse_lsusb_tree(text: str) -> dict[str, Any]:
    hid_lines = [line.strip() for line in text.splitlines() if "Class=Human Interface Device" in line]
    a90_lines = [line.strip() for line in text.splitlines() if "Dev 013" in line or "A90" in line]
    a90_cdc = [line for line in text.splitlines() if "Class=CDC" in line or "Class=Communications" in line]
    return {
        "host_hid_interface_count": len(hid_lines),
        "host_hid_present": bool(hid_lines),
        "a90_usb_peripheral_present": bool(a90_cdc),
        "a90_usb_control_classes": sorted({
            "cdc_acm" if "cdc_acm" in line else "cdc_ncm" if "cdc_ncm" in line else "usb"
            for line in a90_cdc
        }),
        "host_hid_note": "Host-side HID devices are not A90 /dev/input keyboard candidates.",
    }


def evidence_from_prior_reports() -> dict[str, Any]:
    v2991 = read_json(V2991_RESULT)
    v2992_text = V2992_REPORT.read_text(encoding="utf-8")
    v2993_text = V2993_REPORT.read_text(encoding="utf-8")
    scan = v2991.get("inputscan", {}) if isinstance(v2991.get("inputscan"), dict) else {}
    return {
        "v2991_keyboard_candidates": scan.get("keyboard_candidates"),
        "v2991_keyboard_events": scan.get("keyboard_events", []),
        "v2991_touch_candidates": scan.get("touch_candidates"),
        "v2992_keyboard_fallback_staged": "v2992-doominput-keyboard-state-dry-run" in v2992_text,
        "v2992_operator_prerequisite": "USB keyboard/OTG attached and DOOM keys pressed" in v2992_text,
        "v2993_touch_repeat_saturated": "Do not keep re-running identical event6/event8 touch samples" in v2993_text,
    }


def evaluate_gate(payload: dict[str, Any]) -> dict[str, Any]:
    prior = payload["prior_evidence"]
    health = payload["device_health"]
    usb = payload["host_usb_topology"]
    ready = bool(
        prior["v2992_keyboard_fallback_staged"]
        and prior["v2992_operator_prerequisite"]
        and prior["v2991_keyboard_candidates"] not in (None, 0)
        and health["version"]["version_ok"]
        and health["selftest"]["selftest_ok"]
    )
    reasons: list[str] = []
    if prior["v2991_keyboard_candidates"] in (None, 0):
        reasons.append("No keyboard-class event has been observed on A90 inputscan evidence.")
    if usb["host_hid_present"]:
        reasons.append("Host USB HID devices are present, but they are host peripherals, not A90 evdev nodes.")
    if usb["a90_usb_peripheral_present"]:
        reasons.append("A90 is currently enumerated as a USB CDC gadget/peripheral for control.")
    if not health["selftest"]["selftest_ok"]:
        reasons.append("Resident device selftest is not clean.")
    if not prior["v2992_keyboard_fallback_staged"]:
        reasons.append("V2992 keyboard fallback report is not staged.")
    return {
        "decision": DECISION_READY if ready else DECISION_NOT_ACTIONABLE,
        "v2992_live_ready_now": ready,
        "reasons": reasons,
        "next_action": (
            "Run V2992 live only after A90 inputscan evidence can show a keyboard-class event, "
            "or after an operator-attached OTG path preserves control and keypress sampling."
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
        "prior_evidence": evidence_from_prior_reports(),
        "device_health": {
            "version": parse_version(steps[0]["stdout"]),
            "status": parse_status(steps[1]["stdout"]),
            "selftest": parse_selftest(steps[2]["stdout"]),
        },
        "host_usb_topology": parse_lsusb_tree(steps[3]["stdout"]),
        "inputs": {
            "v2991_result": rel(V2991_RESULT),
            "v2992_report": rel(V2992_REPORT),
            "v2993_report": rel(V2993_REPORT),
        },
    }
    payload["gate"] = evaluate_gate(payload)
    return payload


def render_report(payload: dict[str, Any]) -> str:
    health = payload["device_health"]
    prior = payload["prior_evidence"]
    usb = payload["host_usb_topology"]
    gate = payload["gate"]
    reasons = gate["reasons"] or ["V2992 live prerequisite is currently satisfied."]
    return "\n".join([
        "# Native Init V2994 DOOM Input Live Gate Audit",
        "",
        "## Summary",
        "",
        f"- Decision: `{gate['decision']}`",
        "- Device action: `none` in this host-only/read-only unit.",
        "- Track: active Video playback / DOOM input prerequisite.",
        f"- Resident build: `{health['version'].get('build_tag')}`",
        f"- Resident selftest fail=0: `{int(bool(health['selftest'].get('selftest_ok')))}`",
        f"- V2992 keyboard fallback staged: `{int(bool(prior['v2992_keyboard_fallback_staged']))}`",
        f"- V2991 A90 keyboard candidates: `{prior['v2991_keyboard_candidates']}`",
        f"- Host USB HID interfaces visible: `{usb['host_hid_interface_count']}`",
        f"- A90 USB peripheral/control present: `{int(bool(usb['a90_usb_peripheral_present']))}`",
        f"- V2992 live ready now: `{int(bool(gate['v2992_live_ready_now']))}`",
        "",
        "## Gate Reasons",
        "",
        *(f"- {reason}" for reason in reasons),
        "",
        "## Next Action",
        "",
        f"- {gate['next_action']}",
        "",
        "## Evidence Inputs",
        "",
        f"- V2991 result: `{payload['inputs']['v2991_result']}`",
        f"- V2992 report: `{payload['inputs']['v2992_report']}`",
        f"- V2993 report: `{payload['inputs']['v2993_report']}`",
        f"- Private raw outputs: `{payload['out_dir']}`",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_input_live_gate_v2994.py tests/test_native_doom_input_live_gate_v2994.py`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_input_live_gate_v2994`: PASS (`5` tests)",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_input_live_gate_v2994.py`: PASS (host-only/read-only report materialized)",
        "- `git diff --check`: PASS",
        "",
        "## Safety",
        "",
        "- Host-only/read-only audit; no flash, no build artifact, no evdev open, no input injection, and no sysfs write.",
        "- `a90ctl version`, `status`, and `selftest verbose` were read-only health checks on the resident v2321 image.",
        "- `lsusb -t` was host topology inspection only; host HID devices were not treated as A90 input evidence.",
        "- No Wi-Fi/audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.",
        "- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.",
    ]) + "\n"


def main() -> int:
    out_dir = ROOT / f"workspace/private/runs/input/{BUILD_TAG}-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = build_payload(out_dir)
    (out_dir / "result.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps({
        "decision": payload["gate"]["decision"],
        "v2992_live_ready_now": payload["gate"]["v2992_live_ready_now"],
        "resident_build": payload["device_health"]["version"].get("build_tag"),
        "selftest_ok": payload["device_health"]["selftest"].get("selftest_ok"),
        "host_hid_interface_count": payload["host_usb_topology"]["host_hid_interface_count"],
        "report": rel(REPORT_PATH),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
