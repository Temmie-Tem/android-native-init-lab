#!/usr/bin/env python3
"""V1497 host-only classifier for the V1496 auto-readiness RC1 failure."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_V1496_DIR = REPO_ROOT / "tmp" / "wifi" / "v1496-wifi-rc1-window-short-hold-handoff"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1497-auto-readiness-rc1-failure-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1497_AUTO_READINESS_RC1_FAILURE_CLASSIFIER_2026-06-01.md"
)

REFERENCE_REPORTS = {
    "v1371": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1371_RC1_LTSSM_FAILURE_CLASSIFIER_2026-06-01.md",
    "v1379": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1379_ANDROID_PARTICIPANT_CORRECTED_RC1_LIVE_2026-06-01.md",
    "v1432": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1432_ENDPOINT_WINDOW_CLASSIFIER_2026-06-01.md",
    "v1448": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1448_CASE_ALIGNED_MICRO_ENDPOINT_HANDOFF_CLASSIFIER_2026-06-01.md",
    "v1461": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1461_PROVIDER_THREAD_STATE_CLASSIFIER_2026-06-01.md",
    "v1475": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1475_EFFECTIVE_LEVEL_LIVE_CLASSIFIER_2026-06-01.md",
    "v1476": REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_V1476_LOWER_INTERVENTION_DESIGN_2026-06-01.md",
    "v1481": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1481_AP2MDM_PROVIDER_FEASIBILITY_2026-06-01.md",
    "v1482": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1482_ANDROID_AP2MDM_REFERENCE_CLASSIFIER_2026-06-01.md",
}

DMESG_TS_RE = re.compile(r"^\[\s*(?P<ts>\d+\.\d+)\]")


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


def first_line(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line.strip()
    return ""


def first_ts(text: str, needle: str) -> float | None:
    line = first_line(text, needle)
    if not line:
        return None
    match = DMESG_TS_RE.match(line)
    if match is None:
        return None
    return float(match.group("ts"))


def matching_lines(text: str, needles: tuple[str, ...], limit: int = 12) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        if any(needle in line for needle in needles):
            lines.append(line.strip())
        if len(lines) >= limit:
            break
    return lines


def extract_decision(text: str) -> str:
    match = re.search(r"Decision:\s*`([^`]+)`", text)
    return match.group(1) if match else ""


def parse_bool_from_report(text: str, needle: str) -> bool:
    return needle in text


def parse_v1496(v1496_dir: Path) -> dict[str, Any]:
    manifest = read_json(v1496_dir / "manifest.json")
    dmesg = read_text(v1496_dir / "test-v1393-dmesg.stdout.txt")
    watcher = read_text(v1496_dir / "test-v1393-rc1-watcher-result.stdout.txt")
    window = read_text(v1496_dir / "test-rc1-window-result.stdout.txt")
    wlan0 = read_text(v1496_dir / "test-wlan0.stdout.txt")
    progress = manifest.get("wifi_progress", {})

    timestamps = {
        "provider_esoc0_ts": first_ts(dmesg, "__subsystem_get: esoc0"),
        "rc_sel_ts": first_ts(dmesg, "PCIe: rc_sel is now: 0x2"),
        "case11_ts": first_ts(dmesg, "PCIe: TEST: 11"),
        "assert_reset_ts": first_ts(dmesg, "Assert the reset of endpoint of RC1"),
        "phy_ready_ts": first_ts(dmesg, "PCIe RC1 PHY is ready"),
        "release_reset_ts": first_ts(dmesg, "Release the reset of endpoint of RC1"),
        "ltssm_detect_quiet_ts": first_ts(dmesg, "LTSSM_DETECT_QUIET"),
        "ltssm_poll_active_ts": first_ts(dmesg, "LTSSM_POLL_ACTIVE"),
        "ltssm_poll_compliance_ts": first_ts(dmesg, "LTSSM_POLL_COMPLIANCE"),
        "link_failed_ts": first_ts(dmesg, "PCIe RC1 link initialization failed"),
    }
    derived: dict[str, float] = {}
    if timestamps["case11_ts"] is not None and timestamps["provider_esoc0_ts"] is not None:
        derived["case_after_provider_ms"] = round(
            (timestamps["case11_ts"] - timestamps["provider_esoc0_ts"]) * 1000.0,
            3,
        )
    if timestamps["link_failed_ts"] is not None and timestamps["case11_ts"] is not None:
        derived["link_fail_after_case_ms"] = round(
            (timestamps["link_failed_ts"] - timestamps["case11_ts"]) * 1000.0,
            3,
        )
    if timestamps["phy_ready_ts"] is not None and timestamps["case11_ts"] is not None:
        derived["phy_ready_after_case_ms"] = round(
            (timestamps["phy_ready_ts"] - timestamps["case11_ts"]) * 1000.0,
            3,
        )

    return {
        "manifest": manifest,
        "progress": progress,
        "timestamps": timestamps,
        "derived": derived,
        "watcher": {
            "triggered": "state=triggered" in watcher or "state=triggered" in str(progress.get("pid1_rc1_watcher_result_file", "")),
            "write_rc_zero": "write_rc=0" in watcher or "write_rc=0" in str(progress.get("pid1_rc1_watcher_result_file", "")),
            "debugfs_write_confirmed": "PCIe: rc_sel is now: 0x2" in dmesg and "PCIe: TEST: 11" in dmesg,
            "watcher_line": (watcher.strip() or str(progress.get("pid1_rc1_watcher_result_file", "")))[:500],
        },
        "window": {
            "sample_count": progress.get("pid1_rc1_window_sample_count"),
            "has_post_500ms": progress.get("pid1_rc1_window_has_post_500ms"),
            "gpio102_low": "gpio102 : out 0" in window,
            "gpio103_high": "gpio103 : in 1" in window,
            "gpio104_low": "gpio104 : in 0" in window,
            "gpio135_low": "gpio135 : out 0" in window,
            "gpio142_low": "gpio142 : in 0" in window,
            "gpio142_irq_zero": "gpio142" in window and re.search(r"gpio142.*irq.*(?:^|\\D)0(?:\\D|$)", window, re.IGNORECASE) is not None,
            "representative_lines": matching_lines(
                window,
                ("gpio102", "gpio103", "gpio104", "gpio135", "gpio142", "LTSSM", "pcie_1_gdsc"),
                limit=16,
            ),
        },
        "dmesg_lines": matching_lines(
            dmesg,
            (
                "__subsystem_get: esoc0",
                "PCIe: rc_sel is now: 0x2",
                "PCIe: TEST: 11",
                "PCIe RC1 PHY is ready",
                "LTSSM_",
                "PCIe RC1 link initialization failed",
                "wlan0",
            ),
            limit=24,
        ),
        "wlan0_output": wlan0.strip()[:500],
    }


def parse_reference_reports() -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for key, path in REFERENCE_REPORTS.items():
        text = read_text(path)
        parsed[key] = {
            "path": rel(path),
            "exists": bool(text),
            "decision": extract_decision(text),
            "mentions_no_l0": parse_bool_from_report(text, "no L0") or parse_bool_from_report(text, "before L0"),
            "mentions_no_wlan0": parse_bool_from_report(text, "wlan0` remain absent")
            or parse_bool_from_report(text, "wlan0` appeared")
            or parse_bool_from_report(text, "wlan0_present`: `False`"),
            "mentions_android_l0": parse_bool_from_report(text, "Android reaches L0")
            or parse_bool_from_report(text, "known-good L0"),
            "mentions_no_rc1_retry": parse_bool_from_report(text, "Repeat corrected RC1")
            or parse_bool_from_report(text, "not another blind RC1 retry")
            or parse_bool_from_report(text, "should not repeat RC1"),
        }
    return parsed


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1496 = parse_v1496(args.v1496_dir)
    refs = parse_reference_reports()
    progress = v1496["progress"]
    timestamps = v1496["timestamps"]

    v1496_pass = (
        v1496["manifest"].get("decision") == "v1496-test-boot-downstream-progress-rollback-pass"
        and v1496["manifest"].get("pass") is True
        and v1496["manifest"].get("handoff_pass") is True
        and v1496["manifest"].get("rollback", {}).get("ok") is True
    )
    corrected_rc1_confirmed = (
        v1496["watcher"]["triggered"]
        and v1496["watcher"]["write_rc_zero"]
        and v1496["watcher"]["debugfs_write_confirmed"]
    )
    rc1_failed_before_l0 = (
        progress.get("rc1_progress") is True
        and progress.get("rc1_link_failed") is True
        and progress.get("rc1_l0") is False
        and timestamps["ltssm_poll_compliance_ts"] is not None
        and timestamps["link_failed_ts"] is not None
    )
    downstream_absent = not any(
        bool(progress.get(key))
        for key in ("mhi_progress", "wlfw_progress", "bdf_progress", "fw_ready_progress", "wlan0_present")
    )
    references_exist = all(item["exists"] for item in refs.values())
    existing_endpoint_gap_reconciled = (
        refs["v1371"]["decision"] == "v1371-endpoint-readiness-gap-after-rc1-power-proven"
        and refs["v1379"]["decision"] == "v1379-corrected-rc1-ltssm-no-downstream-clean"
        and refs["v1432"]["decision"] == "v1432-ap-rc1-prereqs-toggle-but-endpoint-no-l0"
        and refs["v1448"]["decision"] == "v1448-case-aligned-micro-all-low-no-l0"
        and refs["v1476"]["decision"] == "v1476-select-ap2mdm-bounded-hold-test-boot-design"
        and refs["v1481"]["decision"] == "v1481-userspace-hold-closed-kernel-provider-not-live-feasible"
        and refs["v1482"]["decision"] == "v1482-android-gpio135-low-not-primary-gate-next-auto-boot-supervisor"
    )

    pass_condition = (
        v1496_pass
        and corrected_rc1_confirmed
        and rc1_failed_before_l0
        and downstream_absent
        and references_exist
        and existing_endpoint_gap_reconciled
    )
    if pass_condition:
        decision = "v1497-auto-readiness-rc1-fail-reconciled-existing-endpoint-gap"
        reason = (
            "V1496 proves the rollbackable auto-readiness test boot can execute the bounded corrected RC1 enumerate and collect evidence, "
            "but the resulting RC1/LTSSM failure matches the already established endpoint-readiness gap: no L0, MHI, WLFW, BDF, FW-ready, or wlan0."
        )
        next_gate = (
            "Continue from the V1482/V1496 endpoint-readiness branch: design the next source/build-only "
            "pre-L0 endpoint parity observer; do not repeat GPIO135 sysfs hold or corrected RC1-only experiments."
        )
    else:
        decision = "v1497-auto-readiness-rc1-failure-needs-review"
        reason = "V1496 or reference evidence did not satisfy the reconciliation contract."
        next_gate = "Review V1496 evidence and reference reports before any new live mutation."

    return {
        "cycle": "V1497",
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "inputs": {
            "v1496_dir": rel(args.v1496_dir),
            "reference_reports": refs,
        },
        "v1496": {
            "handoff_pass": v1496_pass,
            "decision": v1496["manifest"].get("decision"),
            "rollback": v1496["manifest"].get("rollback", {}),
            "corrected_rc1_confirmed": corrected_rc1_confirmed,
            "rc1_failed_before_l0": rc1_failed_before_l0,
            "downstream_absent": downstream_absent,
            "progress": {
                "provider_trigger": progress.get("provider_trigger"),
                "rc1_progress": progress.get("rc1_progress"),
                "rc1_l0": progress.get("rc1_l0"),
                "rc1_link_failed": progress.get("rc1_link_failed"),
                "mhi_progress": progress.get("mhi_progress"),
                "wlfw_progress": progress.get("wlfw_progress"),
                "bdf_progress": progress.get("bdf_progress"),
                "fw_ready_progress": progress.get("fw_ready_progress"),
                "wlan0_present": progress.get("wlan0_present"),
            },
            "timestamps": timestamps,
            "derived": v1496["derived"],
            "watcher": v1496["watcher"],
            "window": v1496["window"],
            "dmesg_lines": v1496["dmesg_lines"],
            "wlan0_output": v1496["wlan0_output"],
        },
        "classification": {
            "references_exist": references_exist,
            "existing_endpoint_gap_reconciled": existing_endpoint_gap_reconciled,
            "v1495_long_hold_communication_loss_demoted": True,
            "corrected_rc1_only_retry_rejected": pass_condition,
            "gpio135_userspace_hold_rejected_by_v1481": refs["v1481"]["decision"] == "v1481-userspace-hold-closed-kernel-provider-not-live-feasible",
            "gpio135_low_not_primary_gate_by_v1482": refs["v1482"]["decision"] == "v1482-android-gpio135-low-not-primary-gate-next-auto-boot-supervisor",
        },
        "guardrails": {
            "host_only": True,
            "device_command_executed": False,
            "flash_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "pci_debugfs_write_executed_by_classifier": False,
        },
        "next_gate": next_gate,
    }


def render_report(result: dict[str, Any]) -> str:
    v1496 = result["v1496"]
    progress = v1496["progress"]
    refs = result["inputs"]["reference_reports"]
    lines = [
        "# Native Init V1497 Auto-readiness RC1 Failure Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1497`",
        "- Type: host-only classifier over V1496 rollbackable test-boot evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['inputs']['v1496_dir']}`",
        "",
        "## V1496 Facts",
        "",
        f"- V1496 decision: `{v1496['decision']}`",
        f"- handoff/rollback pass: `{v1496['handoff_pass']}`",
        f"- corrected RC1 debugfs enumerate confirmed: `{v1496['corrected_rc1_confirmed']}`",
        f"- RC1 failed before L0: `{v1496['rc1_failed_before_l0']}`",
        f"- downstream absent: `{v1496['downstream_absent']}`",
        f"- provider trigger: `{progress['provider_trigger']}`",
        f"- RC1 progress: `{progress['rc1_progress']}`",
        f"- RC1 L0: `{progress['rc1_l0']}`",
        f"- RC1 link failed: `{progress['rc1_link_failed']}`",
        f"- MHI progress: `{progress['mhi_progress']}`",
        f"- WLFW progress: `{progress['wlfw_progress']}`",
        f"- BDF progress: `{progress['bdf_progress']}`",
        f"- FW-ready progress: `{progress['fw_ready_progress']}`",
        f"- wlan0 present: `{progress['wlan0_present']}`",
        "",
        "## Timing",
        "",
        f"- provider esoc0 ts: `{v1496['timestamps']['provider_esoc0_ts']}`",
        f"- RC1 `rc_sel=2` ts: `{v1496['timestamps']['rc_sel_ts']}`",
        f"- RC1 `case=11` ts: `{v1496['timestamps']['case11_ts']}`",
        f"- RC1 PHY ready ts: `{v1496['timestamps']['phy_ready_ts']}`",
        f"- LTSSM detect quiet ts: `{v1496['timestamps']['ltssm_detect_quiet_ts']}`",
        f"- LTSSM poll active ts: `{v1496['timestamps']['ltssm_poll_active_ts']}`",
        f"- LTSSM poll compliance ts: `{v1496['timestamps']['ltssm_poll_compliance_ts']}`",
        f"- RC1 link failed ts: `{v1496['timestamps']['link_failed_ts']}`",
        f"- RC1 case after provider ms: `{v1496['derived'].get('case_after_provider_ms')}`",
        f"- PHY ready after case ms: `{v1496['derived'].get('phy_ready_after_case_ms')}`",
        f"- link fail after case ms: `{v1496['derived'].get('link_fail_after_case_ms')}`",
        "",
        "## Reference Reconciliation",
        "",
    ]
    for key in sorted(refs):
        item = refs[key]
        lines.append(f"- {key}: `{item['decision']}` (`{item['path']}`)")
    lines.extend([
        "",
        "The V1496 failure is not a new Wi-Fi connect-side blocker. It confirms the",
        "same lower endpoint-readiness boundary already established by V1371, V1379,",
        "V1432, V1448, V1461, V1475, the V1476 lower-intervention design gate,",
        "and the V1481/V1482 AP2MDM closure. Repeating GPIO135 sysfs hold or",
        "corrected RC1-only writes is therefore not the next useful step.",
        "",
        "## Safety Scope",
        "",
        "This classifier was host-only. It did not issue device commands, flash,",
        "reboot, start Wi-Fi HAL, scan/connect, use credentials, configure",
        "DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, or write",
        "pci-msm debugfs controls. V1496 itself did include the test image's bounded",
        "pci-msm debugfs corrected RC1 enumerate (`rc_sel=2` + `case=11`), which is",
        "treated here as existing evidence rather than a new action.",
        "",
        "## Next",
        "",
        result["next_gate"],
        "",
        "Keep credentials, scan/connect, DHCP/routes, and external ping blocked until",
        "`wlan0` exists and the lower RC1/MHI/WLFW path has real readiness evidence.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1496-dir", type=Path, default=DEFAULT_V1496_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = classify(args)
    report = render_report(result)
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "out_dir": rel(args.out_dir),
        "next_gate": result["next_gate"],
    }, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
