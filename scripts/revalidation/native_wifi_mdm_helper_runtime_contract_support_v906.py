#!/usr/bin/env python3
"""V906 source/build-only verifier for mdm_helper runtime-contract helper support."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v906-mdm-helper-runtime-contract-support")
LATEST_POINTER = Path("tmp/wifi/latest-v906-mdm-helper-runtime-contract-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v906-execns-helper-v148-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v906-execns-helper-v148-build/build.log")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("--build-artifact", type=Path, default=DEFAULT_BUILD_ARTIFACT)
    parser.add_argument("--build-log", type=Path, default=DEFAULT_BUILD_LOG)
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL) is not None


def run_host(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
    )
    return result.returncode, result.stdout


def sha256(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    digest = hashlib.sha256()
    with resolved.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_function(source: str, name: str) -> str:
    marker = f"static int {name}("
    start = source.find(marker)
    if start < 0:
        return ""
    next_marker = source.find("\nstatic ", start + len(marker))
    return source[start:] if next_marker < 0 else source[start:next_marker]


def classify(source: str, build_log: str, artifact: Path) -> dict[str, Any]:
    runtime_function = extract_function(
        source,
        "run_wifi_companion_mdm_helper_runtime_contract_capture_guarded",
    )
    checks = {
        "execns_version_v148": has(source, r'EXECNS_VERSION\s+"a90_android_execns_probe v148"'),
        "mode_predicate": "wifi-companion-mdm-helper-runtime-contract-capture" in source,
        "allow_flag": "--allow-mdm-helper-runtime-contract-capture" in source,
        "dispatch": "run_wifi_companion_mdm_helper_runtime_contract_capture_guarded" in source,
        "mdm_helper_selinux_mapping": has(
            source,
            r'"/vendor/bin/mdm_helper".*?"/vendor/bin/ks".*?u:r:vendor_mdm_helper:s0',
        ),
        "property_shim_enabled": has(
            source,
            r"property_service_shim_needed.*?is_wifi_companion_mdm_helper_runtime_contract_capture_mode",
        ),
        "mhi_late_mirror": "mirror_mdm_helper_runtime_mhi_pipe_if_present" in runtime_function,
        "pm_service_light_order": "per_mgr_light" in runtime_function,
        "pm_proxy_helper_excluded": (
            "pm_proxy_helper_start_executed=0" in runtime_function
            and "COMPOSITE_ID_PER_PROXY_HELPER" not in runtime_function
        ),
        "controller_subsys_open_excluded": (
            "subsys_esoc0_controller_open_attempted=0" in runtime_function
            and 'open("/dev/subsys_esoc0"' not in runtime_function
            and "open(paths->dev_subsys_esoc0" not in runtime_function
        ),
        "wifi_hal_excluded": "wifi_hal_start_executed=0" in runtime_function,
        "scan_connect_excluded": "scan_connect_linkup=0" in runtime_function,
        "artifact_exists": repo_path(artifact).exists(),
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
    }
    passed = all(checks.values())
    if passed:
        return {
            "decision": "v906-mdm-helper-runtime-contract-support-pass",
            "pass": True,
            "reason": "helper v148 adds fail-closed mdm_helper runtime-contract capture mode with property shim, pm-service-light ordering, mdm_helper/ks context mappings, and no controller subsystem open",
            "next_step": "V907 deploy helper v148 only; no actor start and no Wi-Fi bring-up",
            "checks": checks,
        }
    missing = [name for name, ok in checks.items() if not ok]
    return {
        "decision": "v906-mdm-helper-runtime-contract-support-incomplete",
        "pass": False,
        "reason": "missing source/build support: " + ", ".join(missing),
        "next_step": "repair helper source/build support before deploy",
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[name, value] for name, value in manifest["classification"]["checks"].items()]
    artifact_rows = [
        ["artifact", manifest["artifact"]["path"]],
        ["sha256", manifest["artifact"]["sha256"]],
        ["file_rc", manifest["artifact"]["file_rc"]],
        ["file", manifest["artifact"]["file_output"].strip()],
    ]
    return "\n".join([
        "# V906 mdm_helper Runtime Contract Support",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_contact: `{manifest['device_contact']}`",
        f"- actor_start_executed: `{manifest['actor_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "value"], check_rows),
        "",
        "## Artifact",
        "",
        markdown_table(["field", "value"], artifact_rows),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V906 mdm_helper Runtime Contract Helper Build Report",
        "",
        "## Result",
        "",
        markdown_table(
            ["Unit", "Evidence", "Decision"],
            [[
                "source/build-only verifier",
                "`tmp/wifi/v906-mdm-helper-runtime-contract-support/manifest.json`",
                f"`{manifest['decision']}`",
            ]],
        ),
        "",
        "V906 adds helper `v148` support for the next bounded `mdm_helper` runtime-contract capture gate. No live actor was started in this unit.",
        "",
        "## Implemented",
        "",
        "- Added mode `wifi-companion-mdm-helper-runtime-contract-capture`.",
        "- Added allow flag `--allow-mdm-helper-runtime-contract-capture`.",
        "- Added default source mappings for `/vendor/bin/mdm_helper` and `/vendor/bin/ks` to `u:r:vendor_mdm_helper:s0`.",
        "- Added property-service shim support for the new mode.",
        "- Added `per_mgr_light` before `mdm_helper`, while explicitly excluding `pm_proxy_helper`.",
        "- Added late private `/dev/mhi_0305_01.01.00_pipe_10` mirroring if the global node appears.",
        "- Preserved hard gates: no service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or controller `/dev/subsys_esoc0` open.",
        "",
        "## Build",
        "",
        f"- artifact: `{manifest['artifact']['path']}`",
        f"- sha256: `{manifest['artifact']['sha256']}`",
        "- static check: `statically linked`, `There is no dynamic section`",
        "",
        "## Guardrails",
        "",
        "- No device contact, helper deployment, actor start, eSoC ioctl, subsystem open, daemon start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, reboot, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write, or Wi-Fi bring-up occurred in V906.",
        "",
        "## Validation",
        "",
        "Executed:",
        "",
        "```bash",
        "scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v906-execns-helper-v148-build/a90_android_execns_probe",
        "python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_runtime_contract_support_v906.py",
        "python3 scripts/revalidation/native_wifi_mdm_helper_runtime_contract_support_v906.py",
        "```",
        "",
        "## Next",
        "",
        "V907 should deploy helper `v148` only and verify remote checksum/mode support. Live runtime-contract execution should remain a separate later gate.",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    source = read_text(args.helper_source)
    build_log = read_text(args.build_log)
    artifact = repo_path(args.build_artifact)
    file_rc, file_output = run_host(["file", str(args.build_artifact)])
    classification = classify(source, build_log, args.build_artifact)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "helper_source": str(args.helper_source),
        "build_log": str(args.build_log),
        "artifact": {
            "path": str(args.build_artifact),
            "exists": artifact.exists(),
            "sha256": sha256(args.build_artifact),
            "file_rc": file_rc,
            "file_output": file_output,
        },
        "classification": classification,
        "device_contact": False,
        "helper_deploy_executed": False,
        "live_esoc_ioctl_executed": False,
        "subsystem_open_executed": False,
        "actor_start_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "boot_image_write_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    write_private_text(
        repo_path("docs/reports/NATIVE_INIT_V906_MDM_HELPER_RUNTIME_CONTRACT_HELPER_BUILD_2026-05-26.md"),
        render_report(manifest),
    )
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_contact: {manifest['device_contact']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
