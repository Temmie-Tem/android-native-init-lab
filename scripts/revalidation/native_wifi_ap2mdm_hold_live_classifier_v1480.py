#!/usr/bin/env python3
"""V1480 host-only classifier for V1479 AP2MDM hold live handoff evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1479_DIR = REPO_ROOT / "tmp" / "wifi" / "v1479-wifi-test-boot-ap2mdm-hold-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1480-ap2mdm-hold-live-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1480_AP2MDM_HOLD_LIVE_CLASSIFIER_2026-06-01.md"
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    return json.loads(text)


def int_field(line: str, name: str, default: int | None = None) -> int | None:
    match = re.search(rf"\b{name}=(-?\d+)\b", line)
    if not match:
        return default
    return int(match.group(1))


def find_line(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line.strip()
    return ""


def classify(args: argparse.Namespace) -> dict[str, Any]:
    manifest = read_json(args.v1479_dir / "manifest.json")
    summary_text = read_text(args.v1479_dir / "test-v1393-summary.stdout.txt")
    window_text = read_text(args.v1479_dir / "test-rc1-window-result.stdout.txt")
    progress = manifest.get("wifi_progress", {})

    gate_line = find_line(window_text, "ap2mdm_hold gate_sample=")
    attempt_line = find_line(window_text, "ap2mdm_hold attempt ")
    cleanup_line = find_line(window_text, "ap2mdm_hold cleanup ")
    hold_summary_line = find_line(window_text, "ap2mdm_hold summary ")

    trace_set_high = int_field(gate_line, "trace_set_high")
    debug_gpio135_low = int_field(gate_line, "debug_gpio135_low")
    export_rc = int_field(attempt_line, "export_rc")
    exported = int_field(attempt_line, "exported")
    direction_high_rc = int_field(attempt_line, "direction_high_rc")
    result_rc = int_field(cleanup_line, "result_rc")

    downstream_absent = not any(
        bool(progress.get(key))
        for key in ("rc1_progress", "mhi_progress", "wlfw_progress", "bdf_progress", "fw_ready_progress", "wlan0_present")
    )
    pass_condition = (
        manifest.get("decision") == "v1479-test-boot-provider-trigger-no-downstream-rollback-pass"
        and bool(manifest.get("pass"))
        and bool(manifest.get("rollback", {}).get("ok"))
        and "bounded-v1477-ap2mdm-hold-test" in window_text
        and trace_set_high == 1
        and debug_gpio135_low == 1
        and export_rc == -16
        and exported == 0
        and direction_high_rc == -125
        and result_rc == -16
        and "gpio135 : out 1" not in window_text
        and "gpio142 : in 1" not in window_text
        and "pcie_1_gdsc 0 2 0 0mV" in window_text
        and downstream_absent
    )
    if pass_condition:
        decision = "v1480-ap2mdm-userspace-hold-refused-busy-no-downstream"
        reason = (
            "V1479 reached the AP2MDM hold gate after the provider set-high trace and confirmed GPIO135 low, "
            "but /sys/class/gpio export returned EBUSY, no hold was applied, GPIO135/GPIO142 stayed low, "
            "pcie1 stayed off, and no downstream Wi-Fi markers appeared."
        )
        next_gate = "V1481 host-only kernel-provider feasibility review; do not retry userspace GPIO hold"
    else:
        decision = "v1480-ap2mdm-hold-live-needs-review"
        reason = "V1479 evidence did not satisfy the AP2MDM hold classifier contract."
        next_gate = "review V1479 evidence before another live mutation"

    return {
        "cycle": "V1480",
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "inputs": {
            "v1479_dir": rel(args.v1479_dir),
            "v1479_manifest": rel(args.v1479_dir / "manifest.json"),
        },
        "handoff": {
            "decision": manifest.get("decision"),
            "pass": bool(manifest.get("pass")),
            "rollback": manifest.get("rollback", {}),
            "summary_has_hold_request": "provider_trigger_ap2mdm_hold_requested=1" in summary_text,
        },
        "ap2mdm_hold": {
            "gate_line": gate_line,
            "attempt_line": attempt_line,
            "cleanup_line": cleanup_line,
            "summary_line": hold_summary_line,
            "trace_set_high": trace_set_high,
            "debug_gpio135_low": debug_gpio135_low,
            "export_rc": export_rc,
            "exported": exported,
            "direction_high_rc": direction_high_rc,
            "result_rc": result_rc,
            "gpio135_high_seen": "gpio135 : out 1" in window_text,
            "gpio142_high_seen": "gpio142 : in 1" in window_text,
            "pcie1_gdsc_off_seen": "pcie_1_gdsc 0 2 0 0mV" in window_text,
        },
        "progress": {
            "provider_trigger": progress.get("provider_trigger"),
            "rc1_progress": progress.get("rc1_progress"),
            "mhi_progress": progress.get("mhi_progress"),
            "wlfw_progress": progress.get("wlfw_progress"),
            "bdf_progress": progress.get("bdf_progress"),
            "fw_ready_progress": progress.get("fw_ready_progress"),
            "wlan0_present": progress.get("wlan0_present"),
            "downstream_absent": downstream_absent,
        },
        "guardrails": {
            "host_only_classifier": True,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
        },
        "next_gate": next_gate,
    }


def render_report(result: dict[str, Any]) -> str:
    hold = result["ap2mdm_hold"]
    progress = result["progress"]
    return "\n".join([
        "# Native Init V1480 AP2MDM Hold Live Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1480`",
        "- Type: host-only classifier over V1479 rollbackable live handoff evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        "",
        "## Inputs",
        "",
        f"- V1479 evidence: `{result['inputs']['v1479_dir']}`",
        f"- V1479 manifest: `{result['inputs']['v1479_manifest']}`",
        "",
        "## Handoff",
        "",
        f"- handoff pass: `{result['handoff']['pass']}`",
        f"- V1479 decision: `{result['handoff']['decision']}`",
        f"- rollback: `{result['handoff']['rollback']}`",
        f"- summary has hold request: `{result['handoff']['summary_has_hold_request']}`",
        "",
        "## AP2MDM Hold Gate",
        "",
        f"- gate line: `{hold['gate_line']}`",
        f"- attempt line: `{hold['attempt_line']}`",
        f"- cleanup line: `{hold['cleanup_line']}`",
        f"- summary line: `{hold['summary_line']}`",
        f"- trace set-high seen: `{hold['trace_set_high']}`",
        f"- GPIO135 low before attempt: `{hold['debug_gpio135_low']}`",
        f"- export rc: `{hold['export_rc']}`",
        f"- exported: `{hold['exported']}`",
        f"- direction-high rc: `{hold['direction_high_rc']}`",
        f"- result rc: `{hold['result_rc']}`",
        f"- GPIO135 high seen: `{hold['gpio135_high_seen']}`",
        f"- GPIO142 high seen: `{hold['gpio142_high_seen']}`",
        f"- pcie1 GDSC off seen: `{hold['pcie1_gdsc_off_seen']}`",
        "",
        "## Wi-Fi Progress",
        "",
        f"- provider trigger: `{progress['provider_trigger']}`",
        f"- RC1 progress: `{progress['rc1_progress']}`",
        f"- MHI progress: `{progress['mhi_progress']}`",
        f"- WLFW progress: `{progress['wlfw_progress']}`",
        f"- BDF progress: `{progress['bdf_progress']}`",
        f"- FW-ready progress: `{progress['fw_ready_progress']}`",
        f"- wlan0 present: `{progress['wlan0_present']}`",
        f"- downstream absent: `{progress['downstream_absent']}`",
        "",
        "## Interpretation",
        "",
        "The userspace AP2MDM hold path is not available from the current native",
        "test boot. The kernel-owned GPIO line refuses sysfs export with EBUSY.",
        "That means repeating this exact userspace hold is low value; the next",
        "decision should be whether a kernel-provider-side path is feasible or",
        "whether a different non-GPIO lower prerequisite is missing.",
        "",
        "## Safety Scope",
        "",
        "This classifier was host-only. V1479 itself used only the rollbackable",
        "test-boot handoff and did not start Wi-Fi HAL, scan/connect, use",
        "credentials, configure DHCP/routes, or perform external ping.",
        "",
        "## Next",
        "",
        result["next_gate"],
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1479-dir", type=Path, default=DEFAULT_V1479_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = classify(args)
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(result))
    if args.write_report:
        args.report_path.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "next": result["next_gate"]}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
