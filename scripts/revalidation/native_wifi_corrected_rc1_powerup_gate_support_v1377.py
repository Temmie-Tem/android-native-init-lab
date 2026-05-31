#!/usr/bin/env python3
"""V1377 source/build-only support for corrected RC1 powerup-thread gate."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import write_private_text


OUT_DIR = Path("tmp/wifi/v1377-corrected-rc1-powerup-gate-support")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1377_CORRECTED_RC1_POWERUP_GATE_SUPPORT_2026-06-01.md")
SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
HELPER = Path("stage3/linux_init/helpers/a90_android_execns_probe")
HELPER_VERSIONED = Path("stage3/linux_init/helpers/a90_android_execns_probe_v283")
HELPER_MARKER = "a90_android_execns_probe v283"
HELPER_SHA256 = "985eba4834b3b0324d886df39cecff9811ae183ea800119fdaea2d6ef8431a18"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def sha256(path: Path) -> str:
    return hashlib.sha256(repo_path(path).read_bytes()).hexdigest()


def run_text(cmd: list[str]) -> str:
    return subprocess.run(cmd, cwd=repo_path(Path(".")), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout


def line_no(text: str, needle: str) -> int:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return 0


def classify() -> dict[str, Any]:
    src = read(SOURCE)
    helper_sha = sha256(HELPER) if repo_path(HELPER).exists() else ""
    versioned_sha = sha256(HELPER_VERSIONED) if repo_path(HELPER_VERSIONED).exists() else ""
    strings = run_text(["strings", str(repo_path(HELPER))]) if helper_sha else ""
    file_out = run_text(["file", str(repo_path(HELPER))]) if helper_sha else ""
    readelf = run_text(["readelf", "-d", str(repo_path(HELPER))]) if helper_sha else ""
    checks = {
        "helper_marker_v283": HELPER_MARKER in src and HELPER_MARKER in strings,
        "helper_sha_matches": helper_sha == HELPER_SHA256 and versioned_sha == HELPER_SHA256,
        "static_aarch64": "ELF 64-bit LSB executable, ARM aarch64" in file_out and "statically linked" in file_out,
        "no_dynamic_section": "There is no dynamic section in this file." in readelf,
        "powerup_counter_used": "count_pm_service_powerup_threads()" in src,
        "trigger_accepts_powerup_thread": "pm_service_powerup_thread_count > 0" in src,
        "fd_gate_still_supported": "per_mgr_subsys_esoc0_count > 0" in src,
        "reports_powerup_gate": "gate_pm_service_powerup_thread_count" in src,
        "skip_reason_updated": "pm_service_powerup_not_observed" in src,
        "corrected_rc1_flag_still_present": "--pm-observer-late-per-proxy-corrected-rc1-enumerate" in src,
    }
    passed = all(checks.values())
    return {
        "cycle": "V1377",
        "type": "source/build-only helper support",
        "generated_at": now_iso(),
        "decision": "v1377-helper-v283-powerup-gate-ready" if passed else "v1377-helper-v283-powerup-gate-incomplete",
        "pass": passed,
        "reason": "helper v283 gates corrected RC1 enumerate on pm-service mdm_subsys_powerup observation instead of requiring an already-open /dev/subsys_esoc0 fd" if passed else "one or more v283 powerup gate checks failed",
        "next_step": "V1378 deploy helper v283, then V1379 rerun bounded Android participant corrected RC1 gate" if passed else "repair helper v283 before deploy",
        "helper_sha256": helper_sha,
        "checks": checks,
        "source_locations": {
            "marker": line_no(src, HELPER_MARKER),
            "powerup_counter": line_no(src, "count_pm_service_powerup_threads()"),
            "powerup_gate": line_no(src, "pm_service_powerup_thread_count > 0"),
            "gate_report": line_no(src, "gate_pm_service_powerup_thread_count"),
            "skip_reason": line_no(src, "pm_service_powerup_not_observed"),
        },
        "hard_exclusions": [
            "source/build-only; no device command",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no PMIC/GPIO/GDSC direct write",
            "no eSoC notify or BOOT_DONE spoof",
            "no flash, boot image write, or partition write",
        ],
        "host": collect_host_metadata(),
    }


def table(mapping: dict[str, Any]) -> str:
    return markdown_table(["field", "value"], [[k, v] for k, v in mapping.items()])


def render(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1377 Corrected RC1 Powerup Gate Support",
        "",
        "## Summary",
        "",
        "- Cycle: `V1377`",
        "- Type: source/build-only helper support",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Script: `scripts/revalidation/native_wifi_corrected_rc1_powerup_gate_support_v1377.py`",
        "- Helper: `a90_android_execns_probe v283`",
        f"- SHA256: `{manifest['helper_sha256']}`",
        f"- Reason: {manifest['reason']}",
        f"- Next Step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        table({k: str(v).lower() for k, v in manifest['checks'].items()}),
        "",
        "## Source Locations",
        "",
        table(manifest['source_locations']),
        "",
        "## Hard Exclusions",
        "",
        *[f"- {item}" for item in manifest['hard_exclusions']],
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
