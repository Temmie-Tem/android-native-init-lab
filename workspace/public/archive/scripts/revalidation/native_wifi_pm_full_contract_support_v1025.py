#!/usr/bin/env python3
"""V1025 source/build verifier for Android PM full-contract matrix support."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1025-pm-full-contract-support")
LATEST_POINTER = Path("tmp/wifi/latest-v1025-pm-full-contract-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_LIVE_WRAPPER = Path("scripts/revalidation/native_wifi_cnss_service_manager_matrix_live_v931.py")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v1025-execns-helper-v174-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v1025-execns-helper-v174-build/build.log")
BUILD_SCRIPT = Path("scripts/revalidation/build_android_execns_probe_helper.sh")

NEW_ORDER = "after-mdm-helper-esoc-fd-with-pm-full-contract"
POST_PROVIDER_GATE = "post-provider-no-wlfw"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("--live-wrapper", type=Path, default=DEFAULT_LIVE_WRAPPER)
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


def ordered(text: str, *tokens: str) -> bool:
    offset = -1
    for token in tokens:
        found = text.find(token, offset + 1)
        if found < 0:
            return False
        offset = found
    return True


def classify(source: str, wrapper: str, build_rc: int, build_log: str, artifact: Path) -> dict[str, Any]:
    matrix_fn = extract_static_function(
        source,
        "int",
        "run_wifi_companion_mdm_helper_cnss_before_subsys_trigger_capture_guarded",
    )
    strings_output = artifact_strings(artifact)
    checks = {
        "execns_version_v174": 'EXECNS_VERSION "a90_android_execns_probe v174"' in source,
        "order_usage_exposed": NEW_ORDER in source and POST_PROVIDER_GATE in source,
        "order_validator_accepts_pm_full_contract": f'streq(order, "{NEW_ORDER}")' in source,
        "post_provider_gate_accepts_pm_full_contract": all(
            token in source
            for token in (
                f'streq(cfg->subsys_trigger_gate, "{POST_PROVIDER_GATE}")',
                f'streq(cfg->service_manager_order, "{NEW_ORDER}")',
                "after-mdm-helper-esoc-fd-with-pm-proxy or after-mdm-helper-esoc-fd-with-pm-full-contract",
            )
        ),
        "live_wrapper_accepts_new_order": NEW_ORDER in wrapper,
        "pm_full_contract_child_present": all(
            token in matrix_fn
            for token in (
                "struct composite_child children[12]",
                "struct composite_child *pm_proxy_helper = &children[8]",
                "COMPOSITE_ID_PER_PROXY_HELPER",
                '"/vendor/bin/pm_proxy_helper"',
            )
        ),
        "android_order_modeled_before_mdm_helper": ordered(
            matrix_fn,
            "cnss_before_esoc.pm_proxy_helper_start_attempted=1",
            "cnss_before_esoc.per_mgr_start_attempted=1",
            "cnss_before_esoc.pm_proxy_start_attempted=1",
            "cnss_before_esoc.mdm_helper_start_attempted=1",
        ),
        "subsys_modem_fd_contract_scanned": all(
            token in matrix_fn
            for token in (
                "pm_proxy_helper_subsys_modem_fd_count",
                "per_mgr_subsys_modem_fd_count",
                "pm_full_contract_seen",
                '"/dev/subsys_modem"',
                "cnss_before_esoc.pm_full_contract_poll=%d",
            )
        ),
        "upper_stack_waits_for_pm_contract": all(
            token in matrix_fn
            for token in (
                "(!pm_full_contract_matrix || pm_full_contract_seen) &&",
                "start_cnss_before_esoc_service_manager_trio",
                "cnss_before_esoc.cnss_diag_start_attempted=1",
            )
        ),
        "post_provider_trigger_requires_pm_contract": all(
            token in matrix_fn
            for token in (
                "const bool post_provider_trigger_ready",
                "post_provider_no_wlfw_gate",
                "mdm_esoc_fd_seen",
                "(!pm_full_contract_matrix || pm_full_contract_seen)",
                "pm_proxy_started",
                "service_manager_started",
                "cnss_diag_started",
                "cnss_daemon_started",
            )
        ),
        "fail_closed_result_added": all(
            token in matrix_fn
            for token in (
                "pm-full-contract-missing-no-open",
                "pm-proxy-helper-and-per-mgr-did-not-both-hold-dev-subsys-modem",
            )
        ),
        "cleanup_covers_pm_proxy_helper": all(
            token in matrix_fn
            for token in (
                "(!pm_full_contract_matrix || cnss_before_esoc_child_postflight_safe(pm_proxy_helper))",
                "cnss_before_esoc.pm_proxy_helper.postflight_safe=%d",
                "cnss_before_esoc.pm_proxy_helper_start_executed=%d",
            )
        ),
        "guardrails_still_forbid_linkup": all(
            token in matrix_fn
            for token in (
                "cnss_before_esoc.iwifi_start=0",
                "cnss_before_esoc.qcwlanstate_write=0",
                "cnss_before_esoc.scan_connect_linkup=0",
                "cnss_before_esoc.credentials=0",
                "cnss_before_esoc.dhcp_routing=0",
                "cnss_before_esoc.external_ping=0",
                "cnss_before_esoc.notify_attempted=0",
                "cnss_before_esoc.boot_done_attempted=0",
            )
        ),
        "artifact_exists": repo_path(artifact).exists(),
        "build_passed": build_rc == 0,
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
        "strings_confirm_marker": "a90_android_execns_probe v174" in strings_output,
        "strings_confirm_new_order": NEW_ORDER in strings_output,
        "strings_confirm_pm_contract_result": "pm-full-contract-missing-no-open" in strings_output,
    }
    passed = all(checks.values())
    return {
        "decision": "v1025-pm-full-contract-support-pass"
        if passed
        else "v1025-pm-full-contract-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v174 adds source/build-only support for Android PM full-contract gating before a post-provider subsystem retry"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v174 only, then run a bounded live PM full-contract classifier before any Wi-Fi scan/connect"
            if passed
            else "repair helper v174 PM full-contract support before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[name, "PASS" if ok else "FAIL"] for name, ok in manifest["checks"].items()]
    return "\n".join(
        [
            "# V1025 PM Full-Contract Support",
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
            "- No device command, deploy, daemon start, Wi-Fi HAL live start, scan/connect, credentials, DHCP/routes, external ping, boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write, or live `/dev/subsys_esoc0` open.",
            "- New live order must prove both `pm_proxy_helper` and `pm-service` hold `/dev/subsys_modem` before the post-provider subsystem retry can arm.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    source = read_text(args.helper_source)
    wrapper = read_text(args.live_wrapper)
    build_rc = 0
    build_log = read_text(args.build_log)
    if not args.skip_build:
        build_rc, build_log = build_helper(args.build_artifact, args.build_log)
    classification = classify(source, wrapper, build_rc, build_log, args.build_artifact)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "helper_source": str(repo_path(args.helper_source)),
            "helper_source_sha256": sha256(args.helper_source),
            "live_wrapper": str(repo_path(args.live_wrapper)),
            "build_log": str(repo_path(args.build_log)),
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "deploy_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "build_artifact": str(repo_path(args.build_artifact)),
        "build_artifact_sha256": sha256(args.build_artifact),
        **classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"build_artifact_sha256: {manifest['build_artifact_sha256']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
