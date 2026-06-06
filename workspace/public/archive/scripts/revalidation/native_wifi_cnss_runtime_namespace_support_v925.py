#!/usr/bin/env python3
"""V925 source/build verifier for CNSS runtime namespace and output throttle support."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v925-cnss-runtime-namespace-support")
LATEST_POINTER = Path("tmp/wifi/latest-v925-cnss-runtime-namespace-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v925-execns-helper-v153-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v925-execns-helper-v153-build/build.log")
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


def run_host(command: list[str], timeout: int = 20) -> tuple[int, str]:
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
    build_log_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.chmod(0o700)
    rc, output = run_host([str(BUILD_SCRIPT), str(artifact)], timeout=180)
    build_log_path.write_text(output, encoding="utf-8")
    build_log_path.chmod(0o600)
    if artifact_path.exists():
        artifact_path.chmod(0o700)
    return rc, output


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


def classify(source: str, build_rc: int, build_log: str, artifact: Path) -> dict[str, Any]:
    parse_function = extract_static_function(source, "int", "parse_args")
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
    combined_live_path = run_function + "\n" + child_function
    checks = {
        "execns_version_v153": 'EXECNS_VERSION "a90_android_execns_probe v153"' in source,
        "surface_mode_config": "const char *cnss_surface_mode" in source
        and "cnss_surface_mode_explicit" in source,
        "surface_mode_usage_and_parser": "--cnss-surface-mode full|compact" in source
        and 'strcmp(argv[i], "--cnss-surface-mode")' in source,
        "surface_mode_limited_to_cnss_before": "--cnss-surface-mode is only valid with wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture mode"
        in source,
        "compact_default_for_cnss_before": all(
            token in parse_function
            for token in (
                'cfg->cnss_surface_mode = "compact"',
                'cfg->linkerconfig_mode = "copy-real"',
                'cfg->linkerconfig_source = "/cache/bin/a90_real_ld.config.txt"',
                'cfg->vndk_apex_alias_mode = "v30-to-system-ext-v30"',
                'cfg->android_selinux_context_mode = "service-defaults"',
            )
        ),
        "runtime_namespace_reporting": all(
            token in run_function
            for token in (
                "cnss_before_esoc.surface_mode=%s",
                "cnss_before_esoc.runtime_namespace.linkerconfig_mode=%s",
                "cnss_before_esoc.runtime_namespace.vndk_apex_alias_mode=%s",
                "cnss_before_esoc.runtime_namespace.android_selinux_context_mode=%s",
                "cnss_before_esoc.runtime_namespace.property_root_present=%d",
            )
        ),
        "compact_output_throttle": all(
            token in run_function
            for token in (
                'compact_surface = streq(cfg->cnss_surface_mode, "compact")',
                "cnss_before_esoc.compact_surface_poll=%d",
                "cnss_before_esoc.surface_capture.cnss_before_esoc_before=compact-skipped",
                "cnss_before_esoc.surface_capture.cnss_before_esoc_final=compact-skipped",
                "cnss_before_esoc.surface_poll_count=%d",
            )
        ),
        "full_surface_still_available": ordered(
            run_function,
            "if (compact_surface)",
            "append_wifi_window_surface_capture(stdout_buf, \"cnss_before_esoc_before\")",
        )
        and "--cnss-surface-mode" in source
        and '"full"' in source,
        "wlfw_gate_preserved": ordered(
            run_function,
            "if (wlfw_precondition_observed)",
            "start_cnss_before_esoc_subsys_trigger_child",
        )
        and all(
            token in marker_function
            for token in (
                "cnss-daemon wlfw_start",
                "wlfw_start: Starting",
                "wlfw_service_request",
            )
        ),
        "subsys_open_still_child_only": 'open("/dev/subsys_esoc0", O_RDONLY | O_NONBLOCK | O_CLOEXEC)'
        in child_function
        and "cnss_before_esoc.subsys_esoc0_open_attempted=1" in child_function
        and "cnss_before_esoc.subsys_esoc0_controller_open_attempted=0" in run_function,
        "forbidden_live_expansion_absent": all(
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
        )
        and all(
            token not in combined_live_path
            for token in (
                "A90_ESOC_NOTIFY",
                "A90_ESOC_BOOT_DONE",
                "ESOC_NOTIFY",
                "ESOC_BOOT_DONE",
                "allow_wifi_hal_start_only = true",
                "allow_connect_dhcp_ping = true",
            )
        ),
        "artifact_exists": repo_path(artifact).exists(),
        "build_passed": build_rc == 0,
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
    }
    passed = all(checks.values())
    return {
        "decision": "v925-cnss-runtime-namespace-support-pass"
        if passed
        else "v925-cnss-runtime-namespace-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v153 adds compact CNSS-before-eSoC output and explicit runtime namespace defaults/reporting"
            if passed
            else "missing source/build checks: "
            + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v153 only, then run bounded V926 compact CNSS precondition gate"
            if passed
            else "repair helper v153 source/build support before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V925 CNSS Runtime Namespace Support",
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
                    ["build_rc", manifest["build"]["rc"]],
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
    build_rc = 0
    build_output = ""
    if not args.skip_build:
        build_rc, build_output = build_helper(args.build_artifact, args.build_log)
    else:
        build_output = read_text(args.build_log)
    source = read_text(args.helper_source)
    build_log = read_text(args.build_log)
    file_rc, file_output = run_host(["file", "-L", str(args.build_artifact)])
    classification = classify(source, build_rc, build_log, args.build_artifact)
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
        "build": {
            "script": str(BUILD_SCRIPT),
            "rc": build_rc,
            "output_tail": build_output[-4000:],
        },
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
