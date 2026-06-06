#!/usr/bin/env python3
"""V921 source/build verifier for CNSS-before-eSoC mdm_helper trigger support."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v921-mdm-helper-cnss-before-esoc-support")
LATEST_POINTER = Path("tmp/wifi/latest-v921-mdm-helper-cnss-before-esoc-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v921-execns-helper-v152-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v921-execns-helper-v152-build/build.log")


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


def sha256(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    digest = hashlib.sha256()
    with resolved.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def extract_static_function(source: str, prefix: str, name: str) -> str:
    pattern = rf"\nstatic {re.escape(prefix)}\s+{re.escape(name)}\("
    match = re.search(pattern, source)
    if not match:
        return ""
    start = match.start() + 1
    next_match = re.search(r"\nstatic\s+", source[start + 1 :])
    if not next_match:
        return source[start:]
    return source[start : start + 1 + next_match.start()]


def ordered(text: str, first: str, second: str) -> bool:
    left = text.find(first)
    right = text.find(second)
    return left >= 0 and right >= 0 and left < right


def classify(source: str, build_log: str, artifact: Path) -> dict[str, Any]:
    run_function = extract_static_function(
        source,
        "int",
        "run_wifi_companion_mdm_helper_cnss_before_subsys_trigger_capture_guarded",
    )
    child_function = extract_static_function(
        source,
        "int",
        "start_cnss_before_esoc_subsys_trigger_child",
    )
    marker_function = extract_static_function(
        source,
        "bool",
        "cnss_before_esoc_wlfw_precondition_observed",
    )
    combined = run_function + "\n" + child_function + "\n" + marker_function
    checks = {
        "execns_version_v152": 'EXECNS_VERSION "a90_android_execns_probe v152"' in source,
        "mode_string": "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture" in source,
        "allow_flag": "--allow-mdm-helper-cnss-before-subsys-trigger-capture" in source,
        "config_field": "allow_mdm_helper_cnss_before_subsys_trigger_capture" in source,
        "predicate": "is_wifi_companion_mdm_helper_cnss_before_subsys_trigger_capture_mode" in source,
        "dispatch": "run_wifi_companion_mdm_helper_cnss_before_subsys_trigger_capture_guarded" in source,
        "run_function_present": bool(run_function),
        "child_function_present": bool(child_function),
        "marker_function_present": bool(marker_function),
        "actor_order_tokens": all(
            token in run_function
            for token in (
                "per_mgr_light",
                "/vendor/bin/mdm_helper",
                "/vendor/bin/cnss_diag",
                "/vendor/bin/cnss-daemon",
                "wlfw-precondition-gate",
                "subsys_esoc0-open-child",
            )
        ),
        "wlfw_marker_set": all(
            token in marker_function
            for token in (
                "cnss-daemon wlfw_start",
                "wlfw_start: Starting",
                "wlfw_service_request",
            )
        ),
        "fail_closed_missing_allow": all(
            token in run_function
            for token in (
                "cnss_before_esoc.wlfw_precondition_observed=0",
                "cnss_before_esoc.subsys_esoc0_open_gate=cnss-wlfw-precondition",
                "cnss_before_esoc.subsys_esoc0_open_attempted=0",
            )
        ),
        "open_after_wlfw_gate": ordered(
            run_function,
            "if (wlfw_precondition_observed)",
            "start_cnss_before_esoc_subsys_trigger_child",
        ),
        "subsys_open_isolated_to_child": (
            'open("/dev/subsys_esoc0", O_RDONLY | O_NONBLOCK | O_CLOEXEC)' in child_function
            and "cnss_before_esoc.subsys_esoc0_open_attempted=1" in child_function
        ),
        "no_notify_or_boot_done_spoof": all(
            token not in combined
            for token in (
                "A90_ESOC_NOTIFY",
                "A90_ESOC_BOOT_DONE",
                "ESOC_NOTIFY",
                "ESOC_BOOT_DONE",
            )
        ),
        "forbidden_counters": all(
            token in run_function
            for token in (
                "service_manager_start_executed=0",
                "wifi_hal_start_executed=0",
                "scan_connect_linkup=0",
                "credentials=0",
                "dhcp_routing=0",
                "external_ping=0",
                "notify_attempted=0",
                "boot_done_attempted=0",
            )
        ),
        "observability": all(
            token in run_function
            for token in (
                "append_wifi_window_surface_capture",
                "append_wifi_cnss2_focus_capture",
                "append_subsys_hold_snapshot",
                "append_generic_stall_snapshot_capture",
                "append_proc_fd_target_match_scan",
            )
        ),
        "cleanup_reboot_contract": "result=reboot-required" in run_function
        and "actor-or-trigger-not-proven-stopped" in run_function,
        "artifact_exists": repo_path(artifact).exists(),
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
    }
    passed = all(checks.values())
    return {
        "decision": "v921-mdm-helper-cnss-before-esoc-support-pass"
        if passed
        else "v921-mdm-helper-cnss-before-esoc-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v152 adds CNSS/WLFW-precondition-gated /dev/subsys_esoc0 support with fail-closed no-open paths"
            if passed
            else "missing source/build checks: "
            + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v152 only, then run bounded live V923 precondition gate"
            if passed
            else "repair helper v152 source/build support before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V921 mdm_helper CNSS-before-eSoC Support",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            "## Checks",
            "",
            markdown_table(
                ["check", "value"],
                [[key, value] for key, value in manifest["classification"]["checks"].items()],
            ),
            "",
            "## Artifact",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["path", manifest["artifact"]["path"]],
                    ["sha256", manifest["artifact"]["sha256"]],
                    ["file", manifest["artifact"]["file_output"].strip()],
                ],
            ),
            "",
            "## Safety",
            "",
            "- Device contact: false",
            "- Helper deployment: false",
            "- Actor start executed: false",
            "- Wi-Fi bring-up executed: false",
            "- Boot or partition write: false",
            "- Credentials used: false",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    source = read_text(args.helper_source)
    build_log = read_text(args.build_log)
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
        "classification": classification,
        "artifact": {
            "path": str(args.build_artifact),
            "exists": repo_path(args.build_artifact).exists(),
            "sha256": sha256(args.build_artifact),
            "file_rc": file_rc,
            "file_output": file_output,
        },
        "device_contact": False,
        "helper_deployment": False,
        "actor_start_executed": False,
        "wifi_bringup_executed": False,
        "boot_or_partition_write": False,
        "credentials_used": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
