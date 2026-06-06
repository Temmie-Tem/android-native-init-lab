#!/usr/bin/env python3
"""V1034 source/build verifier for PM SELinux domain-proof allowlist support."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1034-pm-selinux-domain-allowlist-support")
LATEST_POINTER = Path("tmp/wifi/latest-v1034-pm-selinux-domain-allowlist-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v1034-execns-helper-v176-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v1034-execns-helper-v176-build/build.log")
BUILD_SCRIPT = Path("scripts/revalidation/build_android_execns_probe_helper.sh")

PM_CONTEXTS = (
    "u:r:per_proxy_helper:s0",
    "u:r:vendor_per_mgr:s0",
    "u:r:vendor_per_proxy:s0",
    "u:r:vendor_mdm_helper:s0",
)


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
        "execns_version_v176": 'EXECNS_VERSION "a90_android_execns_probe v176"' in source,
        "pm_contexts_in_source_allowlist": all(context in source for context in PM_CONTEXTS),
        "domain_proof_mode_preserved": "selinux-domain-proof" in source,
        "guard_flag_preserved": "--require-android-selinux-exec-match" in source,
        "pm_full_contract_mode_preserved": "after-mdm-helper-esoc-fd-with-pm-full-contract" in source,
        "artifact_exists": repo_path(artifact).exists(),
        "build_passed": build_rc == 0,
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
        "strings_confirm_marker": "a90_android_execns_probe v176" in strings_output,
        "strings_confirm_contexts": all(context in strings_output for context in PM_CONTEXTS),
        "strings_confirm_domain_proof": "selinux-domain-proof" in strings_output,
    }
    passed = all(checks.values())
    return {
        "decision": "v1034-pm-selinux-domain-allowlist-support-pass"
        if passed
        else "v1034-pm-selinux-domain-allowlist-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v176 permits PM contexts in selinux-domain-proof allowlist"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v176, rerun V1033 PM SELinux domain proof, then retry V1032 only if PM domains pass"
            if passed
            else "repair helper v176 PM domain allowlist before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[name, "PASS" if ok else "FAIL"] for name, ok in manifest["checks"].items()]
    return "\n".join([
        "# V1034 PM SELinux Domain Allowlist Support",
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
        "- The patch only expands `selinux-domain-proof` context coverage so the PM domains can be tested before another PM actor live retry.",
        "",
    ])


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
        "pm_contexts": list(PM_CONTEXTS),
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
