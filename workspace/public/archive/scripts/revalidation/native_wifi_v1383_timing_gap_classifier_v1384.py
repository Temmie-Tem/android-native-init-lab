#!/usr/bin/env python3
"""V1384 host-only classifier for the V1383 immediate corrected RC1 timing gap."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import write_private_text


OUT_DIR = Path("tmp/wifi/v1384-v1383-timing-gap-classifier")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1384_V1383_TIMING_GAP_CLASSIFIER_2026-06-01.md")
V1383_MANIFEST = Path("tmp/wifi/v1383-android-participant-immediate-corrected-rc1-live/manifest.json")
V1383_DMESG = Path("tmp/wifi/v1383-android-participant-immediate-corrected-rc1-live/native/global-dmesg-after-observer.txt")
V1379_MANIFEST = Path("tmp/wifi/v1379-android-participant-corrected-rc1-live/manifest.json")
V1379_DMESG = Path("tmp/wifi/v1379-android-participant-corrected-rc1-live/native/global-dmesg-after-observer.txt")
V1371_REPORT = Path("docs/reports/NATIVE_INIT_V1371_RC1_LTSSM_FAILURE_CLASSIFIER_2026-06-01.md")
V1381_REPORT = Path("docs/reports/NATIVE_INIT_V1381_IMMEDIATE_CORRECTED_RC1_SUPPORT_2026-06-01.md")
V1382_REPORT = Path("docs/reports/NATIVE_INIT_V1382_EXECNS_HELPER_V284_DEPLOY_2026-06-01.md")

TIME_RE = re.compile(r"\[\s*(\d+\.\d+)\]")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
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


def clean_lines(text: str) -> list[str]:
    return ANSI_RE.sub("", text).splitlines()


def first_time(lines: list[str], *needles: str) -> float | None:
    for line in lines:
        if all(needle in line for needle in needles):
            match = TIME_RE.search(line)
            if match:
                return float(match.group(1))
    return None


def first_line(lines: list[str], *needles: str) -> str:
    for line in lines:
        if all(needle in line for needle in needles):
            return line
    return ""


def count_contains(lines: list[str], needle: str) -> int:
    return sum(1 for line in lines if needle in line)


def dmesg_timing(path: Path) -> dict[str, Any]:
    lines = clean_lines(read(path))
    esoc0 = first_time(lines, "__subsystem_get: esoc0")
    test11 = first_time(lines, "PCIe: TEST: 11")
    assert_time = first_time(lines, "Assert the reset of endpoint of RC1")
    phy_ready = first_time(lines, "PCIe RC1 PHY is ready")
    release = first_time(lines, "Release the reset of endpoint of RC1")
    poll_active = first_time(lines, "LTSSM_STATE: LTSSM_POLL_ACTIVE")
    poll_compliance = first_time(lines, "LTSSM_STATE: LTSSM_POLL_COMPLIANCE")
    l0 = first_time(lines, "LTSSM_STATE: LTSSM_L0")
    link_failed = first_time(lines, "link initialization failed")
    return {
        "esoc0_time": esoc0,
        "test11_time": test11,
        "assert_time": assert_time,
        "phy_ready_time": phy_ready,
        "release_time": release,
        "poll_active_time": poll_active,
        "poll_compliance_time": poll_compliance,
        "l0_time": l0,
        "link_failed_time": link_failed,
        "esoc0_to_assert_sec": None if esoc0 is None or assert_time is None else assert_time - esoc0,
        "test11_to_assert_sec": None if test11 is None or assert_time is None else assert_time - test11,
        "assert_to_release_sec": None if assert_time is None or release is None else release - assert_time,
        "release_to_poll_compliance_sec": None if release is None or poll_compliance is None else poll_compliance - release,
        "release_to_link_failed_sec": None if release is None or link_failed is None else link_failed - release,
        "transition_seen": test11 is not None or assert_time is not None or phy_ready is not None,
        "l0_seen": l0 is not None,
        "link_failed_seen": link_failed is not None,
        "counts": {
            "test11": count_contains(lines, "PCIe: TEST: 11"),
            "assert": count_contains(lines, "Assert the reset of endpoint of RC1"),
            "l0": count_contains(lines, "LTSSM_STATE: LTSSM_L0"),
            "link_failed": count_contains(lines, "link initialization failed"),
            "current_gen": count_contains(lines, "Current GEN"),
            "wlan0": count_contains(lines, "wlan0"),
        },
        "lines": {
            "esoc0": first_line(lines, "__subsystem_get: esoc0"),
            "test11": first_line(lines, "PCIe: TEST: 11"),
            "assert": first_line(lines, "Assert the reset of endpoint of RC1"),
            "release": first_line(lines, "Release the reset of endpoint of RC1"),
            "poll_compliance": first_line(lines, "LTSSM_STATE: LTSSM_POLL_COMPLIANCE"),
            "link_failed": first_line(lines, "link initialization failed"),
        },
    }


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def classify() -> dict[str, Any]:
    v1383 = load_json(V1383_MANIFEST)
    v1379 = load_json(V1379_MANIFEST)
    v1383_timing = dmesg_timing(V1383_DMESG)
    v1379_timing = dmesg_timing(V1379_DMESG)
    v1371_text = read(V1371_REPORT)
    v1381_text = read(V1381_REPORT)
    v1382_text = read(V1382_REPORT)

    android_esoc0_to_assert = float(ANDROID_DELTA_RE.search(v1371_text).group(1))
    android_release_to_l0 = float(ANDROID_RELEASE_L0_RE.search(v1371_text).group(1))
    v1383_delta = v1383_timing["esoc0_to_assert_sec"]
    v1379_delta = v1379_timing["esoc0_to_assert_sec"]
    improvement = None if v1379_delta is None or v1383_delta is None else v1379_delta - v1383_delta
    ratio = None if v1383_delta is None else v1383_delta / android_esoc0_to_assert

    corrected = v1383.get("corrected_rc1_enumerate") or {}
    sampler = v1383.get("response_sampler") or {}
    checks = {
        "v1381_helper_support_passed": "v1381-helper-v284-immediate-corrected-rc1-ready" in v1381_text,
        "v1382_deploy_passed": "execns-helper-v284-deploy-pass" in v1382_text,
        "v1383_live_passed": v1383.get("pass") is True,
        "v1383_immediate_flag_in_child": (v1383.get("current_route") or {}).get("corrected_rc1_flag_in_child_script") == 1,
        "v1383_corrected_triggered": corrected.get("triggered") is True,
        "v1383_powerup_gate_positive": int(corrected.get("gate_pm_service_powerup_thread_count", -1)) > 0,
        "v1383_write_ok": corrected.get("rc_sel_rc") == 0 and corrected.get("case_rc") == 0,
        "v1383_dmesg_transition_seen": v1383_timing["transition_seen"] is True,
        "v1383_no_l0": v1383_timing["l0_seen"] is False and v1383_timing["link_failed_seen"] is True,
        "v1383_no_downstream": (
            int(sampler.get("timing_gpio142_irq_delta", 0)) == 0
            and int(sampler.get("timing_pci_dev_max", 0)) == 0
            and int(sampler.get("timing_mhi_bus_max", 0)) == 0
            and not bool(sampler.get("timing_mhi_pipe_seen"))
            and int(sampler.get("timing_ks_process_max", 0)) == 0
            and int(sampler.get("timing_wlfw_kmsg_max", 0)) == 0
            and not bool(sampler.get("timing_wlan0_seen"))
        ),
        "v1383_still_late_vs_android": ratio is not None and ratio > 4.0,
        "v1383_not_substantially_better_than_v1379": improvement is not None and improvement < 1.0,
        "host_only": True,
    }
    passed = all(checks.values())
    decision = "v1384-immediate-flag-still-too-late-poll-entry-gap" if passed else "v1384-v1383-timing-classifier-incomplete"
    reason = (
        f"V1383 fired corrected RC1 in the first v284 poll and the debugfs write itself reaches RC1 immediately, but RC1 assert still occurred {v1383_delta:.3f}s after esoc0 versus Android's {android_esoc0_to_assert:.3f}s; this is only {improvement:.3f}s faster than V1379 and still fails before L0 with no downstream progress."
        if passed and v1383_delta is not None and improvement is not None
        else "one or more V1384 host-only checks failed"
    )
    return {
        "cycle": "V1384",
        "type": "host-only V1383 timing/gap classifier",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": (
            "V1385 source/build-only: move the RC1 trigger earlier than the late_per_proxy poll loop, or add tight timing instrumentation around per_proxy start and pm-service powerup-thread first observation"
            if passed
            else "repair V1383 evidence parsing before another live mutation"
        ),
        "checks": checks,
        "timing": {
            "android_esoc0_to_assert_sec": android_esoc0_to_assert,
            "android_release_to_l0_sec": android_release_to_l0,
            "v1379_esoc0_to_assert_sec": v1379_delta,
            "v1383_esoc0_to_assert_sec": v1383_delta,
            "v1383_vs_android_ratio": ratio,
            "v1383_improvement_vs_v1379_sec": improvement,
            "v1383_test11_to_assert_sec": v1383_timing["test11_to_assert_sec"],
            "v1383_assert_to_release_sec": v1383_timing["assert_to_release_sec"],
            "v1383_release_to_poll_compliance_sec": v1383_timing["release_to_poll_compliance_sec"],
            "v1383_release_to_link_failed_sec": v1383_timing["release_to_link_failed_sec"],
        },
        "interpretation": {
            "debugfs_write_latency_is_not_primary": v1383_timing["test11_to_assert_sec"] is not None and abs(v1383_timing["test11_to_assert_sec"]) < 0.01,
            "poll_loop_entry_or_per_proxy_ordering_is_primary": ratio is not None and ratio > 4.0,
            "endpoint_l0_still_unproven": v1383_timing["l0_seen"] is False,
            "another_live_retry_without_reordering_is_low_value": True,
        },
        "dmesg_lines": v1383_timing["lines"],
        "source_evidence": {
            "v1383_manifest": str(V1383_MANIFEST),
            "v1383_dmesg": str(V1383_DMESG),
            "v1379_manifest": str(V1379_MANIFEST),
            "v1379_dmesg": str(V1379_DMESG),
            "v1371_report": str(V1371_REPORT),
        },
        "hard_exclusions": [
            "host-only; no device command",
            "no debugfs/sysfs write, rc_sel/case write, or PCI rescan",
            "no PMIC/GPIO/GDSC direct write",
            "no eSoC notify or BOOT_DONE spoof",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
        "host": collect_host_metadata(),
    }


def table(mapping: dict[str, Any]) -> str:
    return markdown_table(["field", "value"], [[k, fmt(v)] for k, v in mapping.items()])


def render_bool_table(mapping: dict[str, bool]) -> str:
    return markdown_table(["check", "pass"], [[k, str(v).lower()] for k, v in mapping.items()])


def render(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1384 V1383 Timing Gap Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1384`",
        "- Type: host-only V1383 timing/gap classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_v1383_timing_gap_classifier_v1384.py`",
        f"- Reason: {manifest['reason']}",
        f"- Next Step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        render_bool_table(manifest["checks"]),
        "",
        "## Timing",
        "",
        table(manifest["timing"]),
        "",
        "## Interpretation",
        "",
        table({k: str(v).lower() for k, v in manifest["interpretation"].items()}),
        "",
        "## Dmesg Evidence",
        "",
        *[f"- `{key}`: {value}" for key, value in manifest["dmesg_lines"].items() if value],
        "",
        "## Hard Exclusions",
        "",
        *[f"- {item}" for item in manifest["hard_exclusions"]],
        "",
    ])


def main() -> int:
    out = repo_path(OUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    manifest = classify()
    write_private_text(out / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(out / "summary.md", render(manifest))
    write_private_text(repo_path(REPORT_PATH), render(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
