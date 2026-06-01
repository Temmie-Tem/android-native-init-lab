#!/usr/bin/env python3
"""V1381 source/build-only support for immediate corrected RC1 enumerate."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import write_private_text


OUT_DIR = Path("tmp/wifi/v1381-immediate-corrected-rc1-support")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1381_IMMEDIATE_CORRECTED_RC1_SUPPORT_2026-06-01.md")
SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
HELPER = Path("stage3/linux_init/helpers/a90_android_execns_probe")
HELPER_VERSIONED = Path("stage3/linux_init/helpers/a90_android_execns_probe_v284")
HELPER_MARKER = "a90_android_execns_probe v284"
HELPER_SHA256 = "da1f8b65cbc3872f7ec31a368bd382720a399d3a785e50ae383c800632047b9f"
V1380_REPORT = Path("docs/reports/NATIVE_INIT_V1380_RC1_LTSSM_PARTICIPANT_GAP_CLASSIFIER_2026-06-01.md")
V1380_DECISION = "v1380-v1379-rc1-action-too-late-for-android-window"
NEW_FLAG = "--pm-observer-late-per-proxy-immediate-corrected-rc1-enumerate"


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
    v1380 = read(V1380_REPORT)
    helper_sha = sha256(HELPER) if repo_path(HELPER).exists() else ""
    versioned_sha = sha256(HELPER_VERSIONED) if repo_path(HELPER_VERSIONED).exists() else ""
    strings = run_text(["strings", str(repo_path(HELPER))]) if helper_sha else ""
    file_out = run_text(["file", str(repo_path(HELPER))]) if helper_sha else ""
    readelf = run_text(["readelf", "-d", str(repo_path(HELPER))]) if helper_sha else ""

    immediate_order = ordered(
        src,
        "pm_service_powerup_thread_count = count_pm_service_powerup_threads();",
        "if (late_per_proxy_immediate_corrected_rc1_enumerate &&",
        "if (!late_per_proxy_lower_sequence_summary_sampler &&",
    )
    delayed_guard_order = ordered(
        src,
        "if (!late_per_proxy_lower_sequence_summary_sampler &&",
        "if (!late_per_proxy_immediate_corrected_rc1_enumerate &&",
        "late_per_proxy_corrected_rc1_enumerate &&",
    )

    checks = {
        "v1380_prerequisite_passed": V1380_DECISION in v1380,
        "helper_marker_v284": HELPER_MARKER in src and HELPER_MARKER in strings,
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
        "immediate_enabled_reported": (
            "response_sampler.immediate_corrected_rc1_enumerate_enabled" in src
            and "response_sampler.immediate_corrected_rc1_enumerate_enabled" in strings
        ),
        "mode_reported": (
            "post_pm_mdm_helper_esoc_observer.late_per_proxy_immediate_corrected_rc1_enumerate" in src
            and "post_pm_mdm_helper_esoc_observer.late_per_proxy_immediate_corrected_rc1_enumerate" in strings
        ),
        "monotonic_timestamp_reported": (
            "pm_service_trigger_observer.corrected_rc1_enumerate.monotonic_ms" in src
            and "pm_service_trigger_observer.corrected_rc1_enumerate.monotonic_ms" in strings
        ),
        "powerup_gate_still_used": (
            "pm_service_powerup_thread_count > 0" in src
            and "gate_pm_service_powerup_thread_count" in src
            and "gate_pm_service_powerup_thread_count" in strings
        ),
        "immediate_before_sampler": immediate_order,
        "delayed_path_guarded_for_legacy_flag": delayed_guard_order,
        "host_only": True,
    }
    passed = all(checks.values())
    return {
        "cycle": "V1381",
        "type": "source/build-only helper support",
        "generated_at": now_iso(),
        "decision": "v1381-helper-v284-immediate-corrected-rc1-ready" if passed else "v1381-helper-v284-immediate-corrected-rc1-incomplete",
        "pass": passed,
        "reason": (
            "helper v284 adds an immediate corrected RC1 enumerate path that fires as soon as the pm-service powerup-thread gate becomes positive, before the response sampler consumes the poll iteration"
            if passed
            else "one or more v284 immediate corrected RC1 checks failed"
        ),
        "next_step": (
            "V1382 deploy helper v284, then V1383 bounded immediate corrected RC1 live gate"
            if passed
            else "repair helper v284 before deploy"
        ),
        "helper_sha256": helper_sha,
        "checks": checks,
        "source_locations": {
            "marker": line_no(src, HELPER_MARKER),
            "new_flag_parse": line_no(src, NEW_FLAG),
            "validation_response_sampler": line_no(src, f"{NEW_FLAG} requires --pm-observer-late-per-proxy-response-sampler"),
            "validation_timing_sampler": line_no(src, f"{NEW_FLAG} requires --pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler"),
            "immediate_mode_const": line_no(src, "const bool late_per_proxy_immediate_corrected_rc1_enumerate"),
            "mode_report": line_no(src, "post_pm_mdm_helper_esoc_observer.late_per_proxy_immediate_corrected_rc1_enumerate"),
            "sampler_enable_report": line_no(src, "pm_service_trigger_observer.response_sampler.immediate_corrected_rc1_enumerate_enabled"),
            "immediate_trigger": line_no(src, "if (late_per_proxy_immediate_corrected_rc1_enumerate &&"),
            "legacy_delayed_guard": line_no(src, "if (!late_per_proxy_immediate_corrected_rc1_enumerate &&"),
            "monotonic_report": line_no(src, "pm_service_trigger_observer.corrected_rc1_enumerate.monotonic_ms"),
        },
        "hard_exclusions": [
            "source/build-only; no device command",
            "no debugfs/sysfs write, rc_sel/case write, or PCI rescan",
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
        "# Native Init V1381 Immediate Corrected RC1 Support",
        "",
        "## Summary",
        "",
        "- Cycle: `V1381`",
        "- Type: source/build-only helper support",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_immediate_corrected_rc1_support_v1381.py`",
        "- Helper: `a90_android_execns_probe v284`",
        f"- SHA256: `{manifest['helper_sha256']}`",
        f"- Reason: {manifest['reason']}",
        f"- Next Step: {manifest['next_step']}",
        "",
        "## Context",
        "",
        "- V1380 showed V1379 wrote corrected RC1 too late: about 4.12 seconds after `__subsystem_get(esoc0)`, versus Android's about 0.255 second reference window.",
        "- V1381 changes only source/build support. It adds an immediate path for the existing corrected RC1 debugfs enumerate write, guarded by the same powerup-thread/fd gate.",
        "- The legacy delayed path remains guarded for non-immediate runs.",
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
