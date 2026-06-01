#!/usr/bin/env python3
"""V1389 source/build-only support for early-observer corrected RC1 trigger."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import write_private_text


OUT_DIR = Path("tmp/wifi/v1389-early-powerup-corrected-rc1-support")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1389_EARLY_POWERUP_CORRECTED_RC1_SUPPORT_2026-06-01.md")
SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
HELPER = Path("stage3/linux_init/helpers/a90_android_execns_probe")
HELPER_VERSIONED = Path("stage3/linux_init/helpers/a90_android_execns_probe_v286")
HELPER_MARKER = "a90_android_execns_probe v286"
HELPER_SHA256 = "e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f"
V1388_REPORT = Path("docs/reports/NATIVE_INIT_V1388_V1387_TIMING_PARTICIPANT_CLASSIFIER_2026-06-01.md")
V1388_DECISION = "v1388-prepoll-gate-works-but-helper-enters-it-too-late"
NEW_FLAG = "--pm-observer-early-powerup-corrected-rc1-enumerate"


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
    for index, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return index
    return 0


def ordered(text: str, *needles: str) -> bool:
    position = -1
    for needle in needles:
        next_position = text.find(needle, position + 1)
        if next_position < 0:
            return False
        position = next_position
    return True


def classify() -> dict[str, Any]:
    source = read(SOURCE)
    v1388 = read(V1388_REPORT)
    helper_sha = sha256(HELPER) if repo_path(HELPER).exists() else ""
    versioned_sha = sha256(HELPER_VERSIONED) if repo_path(HELPER_VERSIONED).exists() else ""
    strings = run_text(["strings", str(repo_path(HELPER))]) if helper_sha else ""
    file_out = run_text(["file", str(repo_path(HELPER))]) if helper_sha else ""
    readelf = run_text(["readelf", "-d", str(repo_path(HELPER))]) if helper_sha else ""

    early_block_before_late_per_proxy = ordered(
        source,
        "mdm_helper_window_snapshot_captured = true;",
        "if (early_powerup_corrected_rc1_enumerate &&",
        "if (late_per_proxy_requested) {",
    )
    early_block_before_response_sampler = ordered(
        source,
        "if (early_powerup_corrected_rc1_enumerate &&",
        "pm_service_trigger_observer.response_sampler.begin=1",
    )
    early_block_reuses_powerup_gate = ordered(
        source,
        "early_per_mgr_subsys_esoc0_count =",
        "early_pm_service_powerup_thread_count = count_pm_service_powerup_threads();",
        "append_late_per_proxy_corrected_rc1_enumerate(",
    )
    early_block_fail_closed = ordered(
        source,
        "pm_service_trigger_observer.corrected_rc1_enumerate.skip_reason=early_powerup_not_observed",
        "late_per_proxy_corrected_rc1_enumerate_done = true;",
    )
    checks = {
        "v1388_prerequisite_passed": V1388_DECISION in v1388,
        "helper_marker_v286": HELPER_MARKER in source and HELPER_MARKER in strings,
        "helper_sha_matches": helper_sha == HELPER_SHA256 and versioned_sha == HELPER_SHA256,
        "static_aarch64": "ELF 64-bit LSB executable, ARM aarch64" in file_out and "statically linked" in file_out,
        "no_dynamic_section": "There is no dynamic section in this file." in readelf,
        "new_flag_in_source": NEW_FLAG in source,
        "new_flag_in_binary": NEW_FLAG in strings,
        "validation_requires_response_sampler": (
            f"{NEW_FLAG} requires --pm-observer-late-per-proxy-response-sampler" in source
            and f"{NEW_FLAG} requires --pm-observer-late-per-proxy-response-sampler" in strings
        ),
        "validation_requires_timing_sampler": (
            f"{NEW_FLAG} requires --pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler" in source
            and f"{NEW_FLAG} requires --pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler" in strings
        ),
        "validation_rejects_ambiguous_combo": "cannot be combined with late/immediate/prepoll corrected RC1 flags" in source,
        "mode_reported": (
            "early_powerup_corrected_rc1_enumerate" in source
            and "early_powerup_corrected_rc1_enumerate" in strings
        ),
        "response_sampler_reports_mode": (
            "response_sampler.early_powerup_corrected_rc1_enumerate_enabled" in source
            and "response_sampler.early_powerup_corrected_rc1_enumerate_enabled" in strings
        ),
        "early_markers_in_binary": (
            "pm_service_trigger_observer.early_powerup_corrected_rc1.begin=1" in strings
            and "pm_service_trigger_observer.early_powerup_corrected_rc1.phase=early_powerup_observer" in strings
            and "pm_service_trigger_observer.early_powerup_corrected_rc1.triggered=%d" in strings
        ),
        "early_block_before_late_per_proxy": early_block_before_late_per_proxy,
        "early_block_before_response_sampler": early_block_before_response_sampler,
        "early_block_reuses_powerup_gate": early_block_reuses_powerup_gate,
        "early_block_fail_closed_no_late_fallback": early_block_fail_closed,
        "response_sampler_preserves_early_write_state": (
            "late_per_proxy_corrected_rc1_enumerate_write_executed" in source
            and "bool *write_executed_out" in source
            and "late_per_proxy_corrected_rc1_enumerate_write_executed ? 1 : 0" in source
        ),
        "legacy_prepoll_path_preserved": "--pm-observer-late-per-proxy-prepoll-corrected-rc1-enumerate" in source,
        "host_only": True,
    }
    passed = all(checks.values())
    return {
        "cycle": "V1389",
        "type": "source/build-only helper support",
        "generated_at": now_iso(),
        "decision": "v1389-helper-v286-early-powerup-corrected-rc1-ready" if passed else "v1389-helper-v286-early-powerup-corrected-rc1-incomplete",
        "pass": passed,
        "reason": (
            "helper v286 adds an opt-in early-observer corrected RC1 trigger that fires from the first visible pm-service mdm_subsys_powerup gate before late_per_proxy response sampling"
            if passed
            else "one or more v286 early-observer corrected RC1 checks failed"
        ),
        "next_step": (
            "V1390 deploy helper v286, then V1391 bounded early-observer corrected RC1 live gate"
            if passed
            else "repair helper v286 before deploy"
        ),
        "helper_sha256": helper_sha,
        "checks": checks,
        "source_locations": {
            "marker": line_no(source, HELPER_MARKER),
            "new_flag_parse": line_no(source, f"strcmp(argv[i], \"{NEW_FLAG}\")"),
            "validation_response_sampler": line_no(source, f"{NEW_FLAG} requires --pm-observer-late-per-proxy-response-sampler"),
            "validation_timing_sampler": line_no(source, f"{NEW_FLAG} requires --pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler"),
            "validation_ambiguous_combo": line_no(source, "cannot be combined with late/immediate/prepoll corrected RC1 flags"),
            "mode_const": line_no(source, "const bool early_powerup_corrected_rc1_enumerate"),
            "mode_report": line_no(source, "post_pm_mdm_helper_esoc_observer.early_powerup_corrected_rc1_enumerate"),
            "early_block": line_no(source, "if (early_powerup_corrected_rc1_enumerate &&"),
            "early_begin_marker": line_no(source, "pm_service_trigger_observer.early_powerup_corrected_rc1.begin=1"),
            "response_sampler_mode": line_no(source, "pm_service_trigger_observer.response_sampler.early_powerup_corrected_rc1_enumerate_enabled"),
            "late_per_proxy_begin": line_no(source, "pm_service_trigger_observer.late_per_proxy.begin=1"),
            "response_sampler_begin": line_no(source, "pm_service_trigger_observer.response_sampler.begin=1"),
        },
        "hard_exclusions": [
            "source/build-only; no device command",
            "no helper deploy",
            "no debugfs/sysfs write, rc_sel/case live write, or PCI rescan",
            "no PMIC/GPIO/GDSC direct write",
            "no eSoC notify or BOOT_DONE spoof",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
        "host": collect_host_metadata(),
    }


def table(mapping: dict[str, Any]) -> str:
    return markdown_table(["field", "value"], [[key, value] for key, value in mapping.items()])


def render(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1389 Early-Observer Corrected RC1 Support",
        "",
        "## Summary",
        "",
        "- Cycle: `V1389`",
        "- Type: source/build-only helper support",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_early_powerup_corrected_rc1_support_v1389.py`",
        "- Helper: `a90_android_execns_probe v286`",
        f"- SHA256: `{manifest['helper_sha256']}`",
        f"- Reason: {manifest['reason']}",
        f"- Next Step: {manifest['next_step']}",
        "",
        "## Context",
        "",
        "- V1388 showed v285's pre-poll writer works but enters too late: about `3.556s` after `__subsystem_get(esoc0)`.",
        "- V1388 also showed an earlier `pm-service` `mdm_subsys_powerup` thread was already observable before the late response sampler.",
        "- V1389 keeps this source/build-only and moves only the opt-in corrected RC1 trigger point.",
        "",
        "## Checks",
        "",
        table({key: str(value).lower() for key, value in manifest["checks"].items()}),
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
    rendered = render(manifest)
    write_private_text(out / "summary.md", rendered)
    write_private_text(repo_path(REPORT_PATH), rendered)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"sha256: {manifest['helper_sha256']}")
    print(f"next: {manifest['next_step']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
