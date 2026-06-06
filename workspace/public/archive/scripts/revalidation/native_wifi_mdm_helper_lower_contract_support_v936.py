#!/usr/bin/env python3
"""V936 source/build verifier for mdm_helper lower-contract diagnostics."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v936-mdm-helper-lower-contract-support")
LATEST_POINTER = Path("tmp/wifi/latest-v936-mdm-helper-lower-contract-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v936-execns-helper-v155-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v936-execns-helper-v155-build/build.log")
BUILD_SCRIPT = Path("scripts/revalidation/build_android_execns_probe_helper.sh")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("--build-artifact", type=Path, default=DEFAULT_BUILD_ARTIFACT)
    parser.add_argument("--build-log", type=Path, default=DEFAULT_BUILD_LOG)
    parser.add_argument("--skip-build", action="store_true")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def sha256(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    digest = hashlib.sha256()
    with resolved.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_host(command: list[str], timeout: int = 30) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def build_helper(artifact: Path, build_log: Path) -> tuple[int, str]:
    artifact_path = repo_path(artifact)
    build_log_path = repo_path(build_log)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.chmod(0o700)
    rc, output = run_host([str(BUILD_SCRIPT), str(artifact)], timeout=180)
    write_private_text(build_log_path, output)
    if artifact_path.exists():
        artifact_path.chmod(0o700)
    return rc, output


def artifact_strings(artifact: Path) -> str:
    if not repo_path(artifact).exists():
        return ""
    rc, output = run_host(["strings", str(artifact)], timeout=20)
    return output if rc == 0 else ""


def extract_static_function(source: str, return_prefix: str, name: str) -> str:
    pattern = rf"\nstatic {re.escape(return_prefix)}\s+{re.escape(name)}\("
    match = re.search(pattern, source)
    if not match:
        return ""
    start = match.start() + 1
    next_match = re.search(r"\nstatic\s+", source[start + 1 :])
    if not next_match:
        return source[start:]
    return source[start : start + 1 + next_match.start()]


def classify(source: str, build_rc: int, build_log: str, artifact: Path) -> dict[str, Any]:
    runtime_fn = extract_static_function(
        source,
        "int",
        "run_wifi_companion_mdm_helper_runtime_contract_capture_guarded",
    )
    snapshot_fn = extract_static_function(
        source,
        "int",
        "append_mdm_helper_lower_contract_snapshot",
    )
    context_scan_fn = extract_static_function(
        source,
        "int",
        "append_mdm_helper_property_context_scan",
    )
    path_stat_fn = extract_static_function(
        source,
        "int",
        "append_mdm_helper_lower_path_stat",
    )
    strings_output = artifact_strings(artifact)
    checks = {
        "execns_version_v155": 'EXECNS_VERSION "a90_android_execns_probe v155"' in source,
        "existing_runtime_mode_preserved": "wifi-companion-mdm-helper-runtime-contract-capture" in source,
        "lower_snapshot_function": all(
            token in snapshot_fn
            for token in (
                "mdm_helper_lower_contract.%s.begin=1",
                "read-only-lower-contract-diagnostics",
                "append_mdm_helper_property_context_scan",
                "append_mdm_helper_lower_path_stat",
            )
        ),
        "property_context_keys": all(
            token in source
            for token in (
                "arm64.memtag.process.mdm_helper",
                "persist.vendor.mdm_helper.fail_action",
                "persist.vendor.mdm_helper.timeout",
                "persist.log.tag.mdm_helper",
                "log.tag.mdm_helper",
            )
        ),
        "property_context_paths": all(
            token in snapshot_fn
            for token in (
                "plat_property_contexts",
                "system_ext_property_contexts",
                "vendor_property_contexts",
                "odm_property_contexts",
            )
        ),
        "property_context_scan_bounded": all(
            token in context_scan_fn
            for token in (
                "line_count < 4096",
                "shown >= 16",
                "truncated",
                "exact.%s=%d",
                "prefix.%s=%d",
            )
        ),
        "lower_path_stats": all(
            token in path_stat_fn
            for token in (
                "dev_major",
                "dev_minor",
                "is_chr",
                "private_esoc0",
                "property_service_socket",
            )
        )
        or all(
            token in snapshot_fn
            for token in (
                "private_esoc0",
                "property_service_socket",
                "sys_bus_esoc",
                "sys_bus_msm_subsys",
            )
        ),
        "runtime_snapshots_inserted": all(
            token in runtime_fn
            for token in (
                'append_mdm_helper_lower_contract_snapshot(stdout_buf, paths, "runtime_contract_before")',
                'append_mdm_helper_lower_contract_snapshot(stdout_buf, paths, "runtime_contract_window")',
                'append_mdm_helper_lower_contract_snapshot(stdout_buf, paths, "runtime_contract_final")',
                'append_mdm_helper_lower_contract_snapshot(stdout_buf, paths, "runtime_contract_after")',
            )
        ),
        "no_new_trigger_or_wifi_bringup": all(
            token in runtime_fn
            for token in (
                "service_manager_start_executed=0",
                "cnss_start_executed=0",
                "wifi_hal_start_executed=0",
                "scan_connect_linkup=0",
                "credentials=0",
                "dhcp_routing=0",
                "external_ping=0",
                "subsys_esoc0_controller_open_attempted=0",
                "notify_attempted=0",
                "boot_done_attempted=0",
            )
        ),
        "artifact_exists": repo_path(artifact).exists(),
        "build_passed": build_rc == 0,
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
        "strings_confirm_marker": "a90_android_execns_probe v155" in strings_output,
        "strings_confirm_lower_contract": "mdm_helper_lower_contract" in strings_output,
        "strings_confirm_existing_runtime_mode": "wifi-companion-mdm-helper-runtime-contract-capture" in strings_output,
    }
    passed = all(checks.values())
    return {
        "decision": "v936-mdm-helper-lower-contract-support-pass"
        if passed
        else "v936-mdm-helper-lower-contract-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v155 adds bounded mdm_helper lower-contract diagnostics to the existing runtime-contract mode without new live trigger expansion"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v155 only, then run bounded runtime-contract capture before any eSoC trigger retry"
            if passed
            else "repair helper v155 lower-contract diagnostics before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [(name, "PASS" if ok else "FAIL") for name, ok in manifest["checks"].items()]
    return "\n".join(
        [
            "# V936 mdm_helper Lower-Contract Support",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- build artifact: `{manifest['build_artifact']}`",
            f"- build sha256: `{manifest['build_artifact_sha256']}`",
            f"- next: {manifest['next_step']}",
            "",
            markdown_table(["check", "result"], rows),
            "",
            "## Guardrails",
            "",
            "- source/build-only verifier",
            "- no device command",
            "- no daemon/service-manager start",
            "- no eSoC ioctl, subsystem open, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.skip_build:
        build_rc = 0 if repo_path(args.build_artifact).exists() else 127
        build_log = read_text(args.build_log)
    else:
        build_rc, build_log = build_helper(args.build_artifact, args.build_log)
    source = read_text(args.helper_source)
    classification = classify(source, build_rc, build_log, args.build_artifact)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "helper_source": str(repo_path(args.helper_source)),
        "build_artifact": str(repo_path(args.build_artifact)),
        "build_artifact_sha256": sha256(args.build_artifact),
        "build_log": str(repo_path(args.build_log)),
        "build_rc": build_rc,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        **classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
