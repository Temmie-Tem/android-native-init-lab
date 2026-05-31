#!/usr/bin/env python3
"""V1380 host-only classifier for the V1379 RC1 LTSSM/participant gap."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import write_private_text


OUT_DIR = Path("tmp/wifi/v1380-rc1-ltssm-participant-gap-classifier")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1380_RC1_LTSSM_PARTICIPANT_GAP_CLASSIFIER_2026-06-01.md")
V1379_MANIFEST = Path("tmp/wifi/v1379-android-participant-corrected-rc1-live/manifest.json")
V1379_DMESG = Path("tmp/wifi/v1379-android-participant-corrected-rc1-live/native/global-dmesg-after-observer.txt")
V1371_REPORT = Path("docs/reports/NATIVE_INIT_V1371_RC1_LTSSM_FAILURE_CLASSIFIER_2026-06-01.md")
V1373_REPORT = Path("docs/reports/NATIVE_INIT_V1373_PROVIDER_PATH_PARITY_CLASSIFIER_2026-06-01.md")
V1379_REPORT = Path("docs/reports/NATIVE_INIT_V1379_ANDROID_PARTICIPANT_CORRECTED_RC1_LIVE_2026-06-01.md")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
TIME_RE = re.compile(r"\[\s*(\d+\.\d+)\]")
ANDROID_DELTA_RE = re.compile(r"\| android_esoc0_to_assert_sec \| ([0-9.]+) \|")
ANDROID_RELEASE_L0_RE = re.compile(r"\| android_release_to_l0_sec \| ([0-9.]+) \|")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(read(path))
    if not isinstance(data, dict):
        raise ValueError(f"expected object in {path}")
    return data


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def first_time(lines: list[str], *needles: str) -> float | None:
    for line in lines:
        if all(needle in line for needle in needles):
            match = TIME_RE.search(line)
            if match:
                return float(match.group(1))
    return None


def count_contains(lines: list[str], needle: str) -> int:
    return sum(1 for line in lines if needle in line)


def first_line(lines: list[str], *needles: str) -> str:
    for line in lines:
        if all(needle in line for needle in needles):
            return line
    return ""


def classify() -> dict[str, Any]:
    v1379 = load_json(V1379_MANIFEST)
    dmesg_lines = strip_ansi(read(V1379_DMESG)).splitlines()
    v1371_text = read(V1371_REPORT)
    v1373_text = read(V1373_REPORT)
    v1379_report = read(V1379_REPORT)

    corrected = v1379.get("corrected_rc1_enumerate") or {}
    sampler = v1379.get("response_sampler") or {}

    esoc0_time = first_time(dmesg_lines, "__subsystem_get: esoc0")
    test11_time = first_time(dmesg_lines, "PCIe: TEST: 11")
    assert_time = first_time(dmesg_lines, "Assert the reset of endpoint of RC1")
    phy_time = first_time(dmesg_lines, "PCIe RC1 PHY is ready")
    release_time = first_time(dmesg_lines, "Release the reset of endpoint of RC1")
    detect_quiet_time = first_time(dmesg_lines, "LTSSM_STATE: LTSSM_DETECT_QUIET")
    poll_active_time = first_time(dmesg_lines, "LTSSM_STATE: LTSSM_POLL_ACTIVE")
    poll_compliance_time = first_time(dmesg_lines, "LTSSM_STATE: LTSSM_POLL_COMPLIANCE")
    l0_time = first_time(dmesg_lines, "LTSSM_STATE: LTSSM_L0")
    link_failed_time = first_time(dmesg_lines, "link initialization failed")

    android_esoc0_to_assert = float(ANDROID_DELTA_RE.search(v1371_text).group(1))
    android_release_to_l0 = float(ANDROID_RELEASE_L0_RE.search(v1371_text).group(1))
    native_esoc0_to_assert = None if esoc0_time is None or assert_time is None else assert_time - esoc0_time
    native_release_to_fail = None if release_time is None or link_failed_time is None else link_failed_time - release_time
    native_release_to_poll_compliance = None if release_time is None or poll_compliance_time is None else poll_compliance_time - release_time
    timing_ratio = None if native_esoc0_to_assert is None else native_esoc0_to_assert / android_esoc0_to_assert

    checks = {
        "v1379_passed": v1379.get("pass") is True,
        "v1379_corrected_triggered": corrected.get("triggered") is True,
        "v1379_powerup_gate_positive": int(corrected.get("gate_pm_service_powerup_thread_count", -1)) > 0,
        "v1379_rc_write_ok": corrected.get("rc_sel_rc") == 0 and corrected.get("case_rc") == 0,
        "v1379_rc1_transition_seen": sampler.get("timing_pcie_rc1_transition_seen") is True,
        "v1379_no_downstream": (
            int(sampler.get("timing_gpio142_irq_delta", 0)) == 0
            and int(sampler.get("timing_pci_dev_max", 0)) == 0
            and int(sampler.get("timing_mhi_bus_max", 0)) == 0
            and not bool(sampler.get("timing_mhi_pipe_seen"))
            and int(sampler.get("timing_wlfw_kmsg_max", 0)) == 0
            and not bool(sampler.get("timing_wlan0_seen"))
        ),
        "v1379_reached_phy_ready": phy_time is not None,
        "v1379_failed_before_l0": l0_time is None and link_failed_time is not None,
        "android_reference_reaches_l0": "android_reached_l0 | true" in v1371_text,
        "v1373_selected_android_participant_combo": "v1373-gap-is-android-participant-plus-rc1-combination" in v1373_text,
        "v1379_timing_is_late_vs_android": timing_ratio is not None and timing_ratio > 4.0,
        "host_only": True,
    }
    passed = all(checks.values())
    decision = "v1380-v1379-rc1-action-too-late-for-android-window" if passed else "v1380-gap-classifier-incomplete"
    reason = (
        f"V1379 fixed the v283 powerup-thread gate and executed rc_sel/case successfully, "
        f"but RC1 enumerate occurred {native_esoc0_to_assert:.3f}s after esoc0 versus Android's "
        f"{android_esoc0_to_assert:.3f}s reference; the resulting LTSSM path still failed before L0 "
        "with no GPIO142/PCI/MHI/WLFW/wlan0 progress."
        if passed and native_esoc0_to_assert is not None
        else "one or more V1380 host-only checks failed"
    )
    next_step = (
        "V1381 source/build-only helper v284: trigger corrected RC1 immediately when the powerup-thread gate becomes positive, then sample the post-enumerate window"
        if passed
        else "repair evidence parsing or rerun host-only classification before live mutation"
    )
    return {
        "cycle": "V1380",
        "type": "host-only RC1 LTSSM/participant gap classifier",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "timing": {
            "v1379_esoc0_time": esoc0_time,
            "v1379_test11_time": test11_time,
            "v1379_assert_time": assert_time,
            "v1379_phy_ready_time": phy_time,
            "v1379_release_time": release_time,
            "v1379_detect_quiet_time": detect_quiet_time,
            "v1379_poll_active_time": poll_active_time,
            "v1379_poll_compliance_time": poll_compliance_time,
            "v1379_l0_time": l0_time,
            "v1379_link_failed_time": link_failed_time,
            "v1379_esoc0_to_assert_sec": native_esoc0_to_assert,
            "v1379_release_to_poll_compliance_sec": native_release_to_poll_compliance,
            "v1379_release_to_link_failed_sec": native_release_to_fail,
            "android_esoc0_to_assert_sec": android_esoc0_to_assert,
            "android_release_to_l0_sec": android_release_to_l0,
            "v1379_vs_android_esoc0_to_assert_ratio": timing_ratio,
        },
        "evidence_lines": {
            "v1379_esoc0": first_line(dmesg_lines, "__subsystem_get: esoc0"),
            "v1379_test11": first_line(dmesg_lines, "PCIe: TEST: 11"),
            "v1379_assert": first_line(dmesg_lines, "Assert the reset of endpoint of RC1"),
            "v1379_phy_ready": first_line(dmesg_lines, "PCIe RC1 PHY is ready"),
            "v1379_release": first_line(dmesg_lines, "Release the reset of endpoint of RC1"),
            "v1379_poll_compliance": first_line(dmesg_lines, "LTSSM_STATE: LTSSM_POLL_COMPLIANCE"),
            "v1379_link_failed": first_line(dmesg_lines, "link initialization failed"),
        },
        "counts": {
            "v1379_l0_lines": count_contains(dmesg_lines, "LTSSM_STATE: LTSSM_L0"),
            "v1379_current_gen_lines": count_contains(dmesg_lines, "Current GEN"),
            "v1379_link_initialized_lines": count_contains(dmesg_lines, "link initialized"),
            "v1379_link_failed_lines": count_contains(dmesg_lines, "link initialization failed"),
        },
        "hard_exclusions": [
            "host-only; no device command",
            "no debugfs/sysfs write, rc_sel/case write, or PCI rescan",
            "no PMIC/GPIO/GDSC direct write",
            "no eSoC notify or BOOT_DONE spoof",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
        "source_reports": {
            "v1371": str(V1371_REPORT),
            "v1373": str(V1373_REPORT),
            "v1379": str(V1379_REPORT),
        },
        "host": collect_host_metadata(),
    }


def render_bool_table(mapping: dict[str, bool]) -> str:
    return markdown_table(["check", "pass"], [[k, str(v).lower()] for k, v in mapping.items()])


def render_timing_table(mapping: dict[str, Any]) -> str:
    return markdown_table(["field", "seconds"], [[k, "" if v is None else f"{v:.6f}" if isinstance(v, float) else v] for k, v in mapping.items()])


def render_kv_table(mapping: dict[str, Any]) -> str:
    return markdown_table(["field", "value"], [[k, v] for k, v in mapping.items()])


def render(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1380 RC1 LTSSM/Participant Gap Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1380`",
        "- Type: host-only RC1 LTSSM/participant gap classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_rc1_ltssm_participant_gap_classifier_v1380.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1380-rc1-ltssm-participant-gap-classifier/manifest.json`",
        "  - `tmp/wifi/v1380-rc1-ltssm-participant-gap-classifier/summary.md`",
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "## Checks",
        "",
        render_bool_table(manifest["checks"]),
        "",
        "## Timing Comparison",
        "",
        render_timing_table(manifest["timing"]),
        "",
        "## Evidence Lines",
        "",
        render_kv_table(manifest["evidence_lines"]),
        "",
        "## Counts",
        "",
        render_kv_table(manifest["counts"]),
        "",
        "## Interpretation",
        "",
        "V1379 did not prove the final Android timing parity path. It proved the corrected RC1 action can be gated by the `pm-service` powerup thread and can transition RC1, but the action happened far later than the Android esoc0-to-RC1 interval captured in V1371. The next implementation should move the corrected RC1 write before expensive surface snapshots/samplers, then observe the post-write window.",
        "",
        "## Hard Exclusions",
        "",
        *[f"- {item}" for item in manifest["hard_exclusions"]],
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
    ])


def main() -> int:
    out = repo_path(OUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    manifest = classify()
    write_private_text(out / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    rendered = render(manifest)
    write_private_text(out / "summary.md", rendered)
    write_private_text(repo_path(REPORT_PATH), rendered)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
