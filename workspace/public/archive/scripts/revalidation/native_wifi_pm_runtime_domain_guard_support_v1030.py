#!/usr/bin/env python3
"""V1030 source/build verifier for fail-closed PM actor SELinux exec matching."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1030-pm-runtime-domain-guard-support")
LATEST_POINTER = Path("tmp/wifi/latest-v1030-pm-runtime-domain-guard-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v1030-execns-helper-v175-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v1030-execns-helper-v175-build/build.log")
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


def classify(source: str, build_rc: int, build_log: str, artifact: Path) -> dict[str, Any]:
    strings_output = artifact_strings(artifact)
    checks = {
        "execns_version_v175": 'EXECNS_VERSION "a90_android_execns_probe v175"' in source,
        "flag_in_usage": "--require-android-selinux-exec-match" in source,
        "config_field_present": "bool require_android_selinux_exec_match;" in source,
        "parser_accepts_flag": 'strcmp(argv[i], "--require-android-selinux-exec-match") == 0' in source,
        "startup_prints_flag": "require_android_selinux_exec_match=%d" in source,
        "exec_match_required_logged": ".selinux_exec.match_required=%d" in source,
        "exec_observed_expected_logged": (
            ".selinux_exec.attr_exec_observed=%s" in source
            and ".selinux_exec.attr_exec_expected=%s" in source
        ),
        "exec_mismatch_fails_before_exec": (
            "if (!streq(exec_value, context))" in source
            and ".selinux_exec.attr_exec_match=0" in source
            and "return -1;" in source
        ),
        "exec_match_pass_logged": ".selinux_exec.attr_exec_match=1" in source,
        "existing_pm_full_contract_order_preserved": "after-mdm-helper-esoc-fd-with-pm-full-contract" in source,
        "existing_pm_guardrails_preserved": all(
            token in source
            for token in (
                "cnss_before_esoc.scan_connect_linkup=0",
                "cnss_before_esoc.credentials=0",
                "cnss_before_esoc.external_ping=0",
            )
        ),
        "artifact_exists": repo_path(artifact).exists(),
        "build_passed": build_rc == 0,
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
        "strings_confirm_marker": "a90_android_execns_probe v175" in strings_output,
        "strings_confirm_flag": "--require-android-selinux-exec-match" in strings_output,
        "strings_confirm_match_key": "selinux_exec.attr_exec_match" in strings_output,
    }
    passed = all(checks.values())
    return {
        "decision": "v1030-pm-runtime-domain-guard-support-pass"
        if passed
        else "v1030-pm-runtime-domain-guard-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v175 can fail closed when requested SELinux exec context is not observable before child exec"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v175 only, then run a bounded domain-guarded PM full-contract proof before any Wi-Fi scan/connect"
            if passed
            else "repair helper v175 SELinux exec-match support before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[name, "PASS" if ok else "FAIL"] for name, ok in manifest["checks"].items()]
    return "\n".join(
        [
            "# V1030 PM Runtime Domain Guard Support",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            f"- artifact: `{manifest['build_artifact']}`",
            f"- artifact_sha256: `{manifest['build_artifact_sha256']}`",
            "",
            markdown_table(["check", "result"], rows),
            "",
            "## Guardrails",
            "",
            "- Source/build-only verifier.",
            "- No device command, deploy, actor start, daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write, or live `/dev/subsys_esoc0` open.",
            "- The new flag only makes child startup fail closed before `execv` when `/proc/self/attr/exec` is not the requested Android service context.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    source = read_text(args.helper_source)
    if args.skip_build:
        build_rc = 0 if repo_path(args.build_artifact).exists() else 1
        build_log = read_text(args.build_log)
    else:
        build_rc, build_log = build_helper(args.build_artifact, args.build_log)
    classification = classify(source, build_rc, build_log, args.build_artifact)
    manifest = {
        "generated_at": now_iso(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "build_artifact": str(args.build_artifact),
        "build_artifact_sha256": sha256(args.build_artifact),
        "build_log": str(args.build_log),
        "checks": classification["checks"],
        "device_commands_executed": False,
        "device_mutations": False,
        "actor_start_executed": False,
        "daemon_start_executed": False,
        "wifi_command_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"artifact: {manifest['build_artifact']}")
    print(f"artifact_sha256: {manifest['build_artifact_sha256']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
