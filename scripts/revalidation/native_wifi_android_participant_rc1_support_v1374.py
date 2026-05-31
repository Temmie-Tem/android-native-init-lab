#!/usr/bin/env python3
"""V1374 source/build-only support for Android participant + corrected RC1 enumerate."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1374-android-participant-rc1-support")
LATEST_POINTER = Path("tmp/wifi/latest-v1374-android-participant-rc1-support.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1374_ANDROID_PARTICIPANT_RC1_SUPPORT_2026-06-01.md")

SOURCE_PATH = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
HELPER_PATH = Path("stage3/linux_init/helpers/a90_android_execns_probe")
HELPER_VERSIONED_PATH = Path("stage3/linux_init/helpers/a90_android_execns_probe_v282")
V1373_MANIFEST = Path("tmp/wifi/v1373-provider-path-parity-classifier/manifest.json")

HELPER_MARKER = "a90_android_execns_probe v282"
NEW_FLAG = "--pm-observer-late-per-proxy-corrected-rc1-enumerate"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path, limit: int = 4 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].decode("utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def sha256_file(path: Path) -> str:
    data = repo_path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()


def run_text(command: list[str]) -> str:
    proc = subprocess.run(
        command,
        cwd=repo_path(Path(".")),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.stdout.strip()


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def source_line(source: str, needle: str) -> int:
    for index, line in enumerate(source.splitlines(), start=1):
        if needle in line:
            return index
    return 0


def classify() -> dict[str, Any]:
    source = read_text(SOURCE_PATH)
    v1373 = read_json(V1373_MANIFEST)
    helper_exists = repo_path(HELPER_PATH).exists()
    versioned_exists = repo_path(HELPER_VERSIONED_PATH).exists()
    helper_sha = sha256_file(HELPER_PATH) if helper_exists else ""
    versioned_sha = sha256_file(HELPER_VERSIONED_PATH) if versioned_exists else ""
    file_output = run_text(["file", str(repo_path(HELPER_PATH))]) if helper_exists else ""
    readelf_output = run_text(["readelf", "-d", str(repo_path(HELPER_PATH))]) if helper_exists else ""

    source_checks = {
        "helper_marker_v282": HELPER_MARKER in source,
        "new_flag_in_usage": NEW_FLAG in source,
        "new_flag_parsed": 'strcmp(argv[i], "--pm-observer-late-per-proxy-corrected-rc1-enumerate")' in source,
        "requires_response_sampler": "requires --pm-observer-late-per-proxy-response-sampler" in source,
        "requires_mdm2ap_timing_sampler": "requires --pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler" in source,
        "uses_corrected_rc1_rc_sel_path": "/sys/kernel/debug/pci-msm/rc_sel" in source,
        "uses_corrected_rc1_case_path": "/sys/kernel/debug/pci-msm/case" in source,
        "writes_rc_sel_bitmask_2": 'write_text_once_errno(rc_sel_path, "2\\n")' in source,
        "writes_case_11_enumerate": 'write_text_once_errno(case_path, "11\\n")' in source,
        "gated_on_pm_service_esoc0": "per_mgr_subsys_esoc0_count > 0" in source,
        "reports_debugfs_write": "corrected_rc1_enumerate.debugfs_control_write_executed" in source,
        "reports_skip_without_esoc0": "skip_reason=per_mgr_subsys_esoc0_not_observed" in source,
    }
    build_checks = {
        "helper_exists": helper_exists,
        "versioned_helper_exists": versioned_exists,
        "helper_and_versioned_sha_match": helper_exists and versioned_exists and helper_sha == versioned_sha,
        "helper_marker_embedded": helper_exists and HELPER_MARKER in run_text(["strings", str(repo_path(HELPER_PATH))]),
        "static_aarch64": "ELF 64-bit LSB executable, ARM aarch64" in file_output and "statically linked" in file_output,
        "no_dynamic_section": "There is no dynamic section in this file." in readelf_output,
    }
    prior_checks = {
        "v1373_passed": v1373.get("decision") == "v1373-gap-is-android-participant-plus-rc1-combination"
        and v1373.get("pass") is True,
    }
    pass_condition = all(source_checks.values()) and all(build_checks.values()) and all(prior_checks.values())
    return {
        "cycle": "V1374",
        "type": "source/build-only helper support",
        "generated_at": now_iso(),
        "decision": "v1374-helper-v282-support-ready" if pass_condition else "v1374-helper-v282-support-incomplete",
        "pass": pass_condition,
        "reason": (
            "helper v282 now supports a helper-side corrected RC1 enumerate action gated on the late per_proxy "
            "window after pm-service is observed holding /dev/subsys_esoc0"
            if pass_condition
            else "one or more source/build gates for helper v282 are missing"
        ),
        "next_step": (
            "V1375 deploy-only helper v282 preflight, then V1376 bounded live Android participant parity + corrected RC1 enumerate gate"
            if pass_condition
            else "repair V1374 helper support before deploy or live execution"
        ),
        "source": {
            "path": str(SOURCE_PATH),
            "marker_line": source_line(source, HELPER_MARKER),
            "flag_line": source_line(source, NEW_FLAG),
            "rc_sel_path_line": source_line(source, "/sys/kernel/debug/pci-msm/rc_sel"),
            "case_path_line": source_line(source, "/sys/kernel/debug/pci-msm/case"),
            "gate_line": source_line(source, "per_mgr_subsys_esoc0_count > 0"),
        },
        "build": {
            "helper_path": str(HELPER_PATH),
            "versioned_helper_path": str(HELPER_VERSIONED_PATH),
            "sha256": helper_sha,
            "versioned_sha256": versioned_sha,
            "file": file_output,
            "readelf_dynamic": readelf_output,
        },
        "source_checks": source_checks,
        "build_checks": build_checks,
        "prior_checks": prior_checks,
        "v1376_live_design": {
            "intent": "start the lower Android participant parity path, wait until pm-service reaches /dev/subsys_esoc0, then trigger corrected RC1 enumerate from inside the same helper process",
            "required_flags": [
                "--allow-post-pm-mdm-helper-esoc-observer",
                "--allow-post-pm-mdm-helper-lower-trace",
                "--pm-observer-start-mdm-helper-after-cnss",
                "--pm-observer-start-cnss-after-provider",
                "--pm-observer-start-cnss-before-per-proxy",
                "--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd",
                "--pm-observer-late-per-proxy-response-sampler",
                "--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler",
                "--pm-observer-late-per-proxy-corrected-rc1-enumerate",
            ],
            "success_signals": [
                "corrected_rc1_enumerate.triggered=1",
                "rc_sel_rc=0 and case_rc=0",
                "RC1 LTSSM reaches L0, or GPIO142/PCI/MHI/WLFW/wlan0 appears",
                "postflight selftest fail=0 after cleanup or reboot recovery",
            ],
            "failure_signals": [
                "per_mgr_subsys_esoc0_count never becomes positive",
                "rc_sel or case write fails",
                "transport loss without recovery evidence",
                "postflight selftest fail>0",
                "unexpected Wi-Fi HAL, scan/connect, DHCP/routes, credential, or external ping activity",
            ],
        },
        "hard_exclusions": [
            "V1374 is source/build-only; no device command is run by this script",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
            "no PMIC/GPIO/GDSC direct writes",
            "no eSoC notify or BOOT_DONE spoof",
            "no flash, boot image write, or partition write",
        ],
        "host": collect_host_metadata(),
    }


def table_from_mapping(mapping: dict[str, Any]) -> list[list[str]]:
    return [[key, bool_text(bool(value))] for key, value in sorted(mapping.items())]


def render_report(manifest: dict[str, Any]) -> str:
    design = manifest.get("v1376_live_design") or {}
    build = manifest.get("build") or {}
    source = manifest.get("source") or {}
    return "\n".join([
        "# Native Init V1374 Android Participant RC1 Support",
        "",
        "## Summary",
        "",
        "- Cycle: `V1374`",
        "- Type: source/build-only helper support",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_android_participant_rc1_support_v1374.py`",
        "- Helper: `a90_android_execns_probe v282`",
        f"- SHA256: `{build.get('sha256', '')}`",
        f"- Reason: {manifest['reason']}",
        f"- Next Step: {manifest['next_step']}",
        "",
        "## Source Checks",
        "",
        markdown_table(["check", "pass"], table_from_mapping(manifest.get("source_checks") or {})),
        "",
        "## Build Checks",
        "",
        markdown_table(["check", "pass"], table_from_mapping(manifest.get("build_checks") or {})),
        "",
        "## Prior Evidence Checks",
        "",
        markdown_table(["check", "pass"], table_from_mapping(manifest.get("prior_checks") or {})),
        "",
        "## Source Locations",
        "",
        markdown_table(["field", "line"], [[key, value] for key, value in source.items()]),
        "",
        "## V1376 Live Design",
        "",
        f"- Intent: {design.get('intent', '')}",
        "- Required flags:",
        *[f"  - `{flag}`" for flag in design.get("required_flags") or []],
        "- Success signals:",
        *[f"  - {item}" for item in design.get("success_signals") or []],
        "- Failure signals:",
        *[f"  - {item}" for item in design.get("failure_signals") or []],
        "",
        "## Hard Exclusions",
        "",
        *[f"- {item}" for item in manifest.get("hard_exclusions") or []],
        "",
        "## Evidence",
        "",
        "- `tmp/wifi/v1374-android-participant-rc1-support/manifest.json`",
        "- `tmp/wifi/v1374-android-participant-rc1-support/summary.md`",
        "",
    ])


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V1374 Android Participant RC1 Support",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- sha256: `{(manifest.get('build') or {}).get('sha256', '')}`",
        f"- next_step: {manifest['next_step']}",
        "",
    ])


def run(args: argparse.Namespace) -> int:
    out_dir = repo_path(Path(args.out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = classify()
    write_private_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "summary.md", render_summary(manifest))
    write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(out_dir) + "\n")
    print(render_summary(manifest))
    return 0 if manifest.get("pass") else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    return parser.parse_args()


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
