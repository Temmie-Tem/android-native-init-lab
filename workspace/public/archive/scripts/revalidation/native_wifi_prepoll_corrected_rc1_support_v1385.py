#!/usr/bin/env python3
"""V1385 source/build-only support for pre-poll corrected RC1 trigger."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import write_private_text


OUT_DIR = Path("tmp/wifi/v1385-prepoll-corrected-rc1-support")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1385_PREPOLL_CORRECTED_RC1_SUPPORT_2026-06-01.md")
SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
HELPER = Path("stage3/linux_init/helpers/a90_android_execns_probe")
HELPER_VERSIONED = Path("stage3/linux_init/helpers/a90_android_execns_probe_v285")
HELPER_MARKER = "a90_android_execns_probe v285"
HELPER_SHA256 = "09827b6f0301f077cd0beb4ed2ae9d48a63662d0ca34eff38245704f2f724cf4"
V1384_REPORT = Path("docs/reports/NATIVE_INIT_V1384_V1383_TIMING_GAP_CLASSIFIER_2026-06-01.md")
V1384_DECISION = "v1384-immediate-flag-still-too-late-poll-entry-gap"
NEW_FLAG = "--pm-observer-late-per-proxy-prepoll-corrected-rc1-enumerate"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def sha256(path: Path) -> str:
    return hashlib.sha256(repo_path(path).read_bytes()).hexdigest()


def run_text(cmd: list[str]) -> str:
    return subprocess.run(
        cmd,
        cwd=repo_path(Path(".")),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    ).stdout


def line_no(text: str, needle: str) -> int:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return 0


def ordered(text: str, *needles: str) -> bool:
    last = -1
    for needle in needles:
        pos = text.find(needle, last + 1)
        if pos < 0:
            return False
        last = pos
    return True


def classify() -> dict[str, Any]:
    src = read(SOURCE)
    v1384 = read(V1384_REPORT)
    helper_sha = sha256(HELPER) if repo_path(HELPER).exists() else ""
    versioned_sha = sha256(HELPER_VERSIONED) if repo_path(HELPER_VERSIONED).exists() else ""
    strings = run_text(["strings", str(repo_path(HELPER))]) if helper_sha else ""
    file_out = run_text(["file", str(repo_path(HELPER))]) if helper_sha else ""
    readelf = run_text(["readelf", "-d", str(repo_path(HELPER))]) if helper_sha else ""

    prepoll_before_main_poll = ordered(
        src,
        "pm_service_trigger_observer.late_per_proxy.started=1",
        "if (late_per_proxy_prepoll_corrected_rc1_enumerate &&",
        "for (int poll = 0; poll < late_per_proxy_poll_max; poll++)",
    )
    prepoll_reuses_gate = ordered(
        src,
        "prepoll_per_mgr_subsys_esoc0_count =",
        "prepoll_pm_service_powerup_thread_count = count_pm_service_powerup_threads();",
        "append_late_per_proxy_corrected_rc1_enumerate(",
    )
    checks = {
        "v1384_prerequisite_passed": V1384_DECISION in v1384,
        "helper_marker_v285": HELPER_MARKER in src and HELPER_MARKER in strings,
        "helper_sha_matches": helper_sha == HELPER_SHA256 and versioned_sha == HELPER_SHA256,
        "static_aarch64": "ELF 64-bit LSB executable, ARM aarch64" in file_out and "statically linked" in file_out,
        "no_dynamic_section": "There is no dynamic section in this file." in readelf,
        "new_flag_in_source": NEW_FLAG in src,
        "new_flag_in_binary": NEW_FLAG in strings,
        "validation_requires_response_sampler": (
            f"{NEW_FLAG} requires --pm-observer-late-per-proxy-response-sampler" in src
            and f"{NEW_FLAG} requires --pm-observer-late-per-proxy-response-sampler" in strings
        ),
        "validation_requires_timing_sampler": (
            f"{NEW_FLAG} requires --pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler" in src
            and f"{NEW_FLAG} requires --pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler" in strings
        ),
        "prepoll_mode_reported": (
            "late_per_proxy_prepoll_corrected_rc1_enumerate" in src
            and "late_per_proxy_prepoll_corrected_rc1_enumerate" in strings
        ),
        "response_sampler_reports_prepoll": (
            "response_sampler.prepoll_corrected_rc1_enumerate_enabled" in src
            and "response_sampler.prepoll_corrected_rc1_enumerate_enabled" in strings
        ),
        "prepoll_markers_in_binary": (
            "pm_service_trigger_observer.prepoll_corrected_rc1.begin=1" in strings
            and "pm_service_trigger_observer.prepoll_corrected_rc1.poll_interval_us=%d" in strings
            and "late_per_proxy_prepoll_%03d" in strings
        ),
        "prepoll_before_main_poll": prepoll_before_main_poll,
        "prepoll_reuses_powerup_or_fd_gate": prepoll_reuses_gate,
        "prepoll_tight_window": "PREPOLL_RC1_POLL_INTERVAL_US = 1000" in src and "PREPOLL_RC1_POLL_MAX = 500" in src,
        "legacy_immediate_path_preserved": "--pm-observer-late-per-proxy-immediate-corrected-rc1-enumerate" in src,
        "host_only": True,
    }
    passed = all(checks.values())
    return {
        "cycle": "V1385",
        "type": "source/build-only helper support",
        "generated_at": now_iso(),
        "decision": "v1385-helper-v285-prepoll-corrected-rc1-ready" if passed else "v1385-helper-v285-prepoll-corrected-rc1-incomplete",
        "pass": passed,
        "reason": (
            "helper v285 adds a pre-poll corrected RC1 path that checks the fd/powerup-thread gate every 1ms immediately after late per_proxy spawn, before the main 50ms sampler loop"
            if passed
            else "one or more v285 pre-poll corrected RC1 checks failed"
        ),
        "next_step": (
            "V1386 deploy helper v285, then V1387 bounded pre-poll corrected RC1 live gate"
            if passed
            else "repair helper v285 before deploy"
        ),
        "helper_sha256": helper_sha,
        "checks": checks,
        "source_locations": {
            "marker": line_no(src, HELPER_MARKER),
            "new_flag_parse": line_no(src, NEW_FLAG),
            "validation_response_sampler": line_no(src, f"{NEW_FLAG} requires --pm-observer-late-per-proxy-response-sampler"),
            "validation_timing_sampler": line_no(src, f"{NEW_FLAG} requires --pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler"),
            "mode_const": line_no(src, "const bool late_per_proxy_prepoll_corrected_rc1_enumerate"),
            "mode_report": line_no(src, "post_pm_mdm_helper_esoc_observer.late_per_proxy_prepoll_corrected_rc1_enumerate"),
            "sampler_report": line_no(src, "pm_service_trigger_observer.response_sampler.prepoll_corrected_rc1_enumerate_enabled"),
            "prepoll_block": line_no(src, "if (late_per_proxy_prepoll_corrected_rc1_enumerate &&"),
            "prepoll_interval": line_no(src, "PREPOLL_RC1_POLL_INTERVAL_US = 1000"),
            "main_poll_loop": line_no(src, "for (int poll = 0; poll < late_per_proxy_poll_max; poll++)"),
        },
        "hard_exclusions": [
            "source/build-only; no device command",
            "no debugfs/sysfs write, rc_sel/case live write, or PCI rescan",
            "no PMIC/GPIO/GDSC direct write",
            "no eSoC notify or BOOT_DONE spoof",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
        "host": collect_host_metadata(),
    }


def table(mapping: dict[str, Any]) -> str:
    return markdown_table(["field", "value"], [[k, v] for k, v in mapping.items()])


def render(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1385 Pre-Poll Corrected RC1 Support",
        "",
        "## Summary",
        "",
        "- Cycle: `V1385`",
        "- Type: source/build-only helper support",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_prepoll_corrected_rc1_support_v1385.py`",
        "- Helper: `a90_android_execns_probe v285`",
        f"- SHA256: `{manifest['helper_sha256']}`",
        f"- Reason: {manifest['reason']}",
        f"- Next Step: {manifest['next_step']}",
        "",
        "## Context",
        "",
        "- V1384 showed V1383 was still too late before the debugfs write; the write itself reached RC1 immediately.",
        "- V1385 keeps this source/build-only and adds a pre-poll path before the main late-per-proxy sampler loop.",
        "- The pre-poll path still requires the same fd or `pm_service_powerup_thread_count` gate before writing corrected RC1.",
        "",
        "## Checks",
        "",
        table({k: str(v).lower() for k, v in manifest["checks"].items()}),
        "",
        "## Source Locations",
        "",
        table(manifest["source_locations"]),
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
    print(f"sha256: {manifest['helper_sha256']}")
    print(f"next: {manifest['next_step']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
