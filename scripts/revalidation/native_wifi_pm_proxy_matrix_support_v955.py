#!/usr/bin/env python3
"""V955 source/build verifier for bounded pm-proxy matrix support."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v955-pm-proxy-matrix-support")
LATEST_POINTER = Path("tmp/wifi/latest-v955-pm-proxy-matrix-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_LIVE_WRAPPER = Path("scripts/revalidation/native_wifi_cnss_service_manager_matrix_live_v931.py")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v955-execns-helper-v159-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v955-execns-helper-v159-build/build.log")
BUILD_SCRIPT = Path("scripts/revalidation/build_android_execns_probe_helper.sh")


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


def token_before(text: str, first: str, second: str) -> bool:
    first_index = text.find(first)
    second_index = text.find(second)
    return first_index >= 0 and second_index >= 0 and first_index < second_index


def classify(
    source: str,
    wrapper: str,
    build_rc: int,
    build_log: str,
    artifact: Path,
) -> dict[str, Any]:
    matrix_fn = extract_static_function(
        source,
        "int",
        "run_wifi_companion_mdm_helper_cnss_before_subsys_trigger_capture_guarded",
    )
    strings_output = artifact_strings(artifact)
    pm_proxy_order = "after-mdm-helper-esoc-fd-with-pm-proxy"
    checks = {
        "execns_version_v159": 'EXECNS_VERSION "a90_android_execns_probe v159"' in source,
        "order_enum_exposed": f"--service-manager-order none|before-cnss|after-cnss|after-mdm-helper-esoc-fd|{pm_proxy_order}" in source,
        "order_validator_accepts_pm_proxy": f'streq(order, "{pm_proxy_order}")' in source,
        "live_wrapper_accepts_pm_proxy_order": pm_proxy_order in wrapper,
        "matrix_child_count_includes_pm_proxy": all(
            token in matrix_fn
            for token in (
                "struct composite_child children[8]",
                'struct composite_child *pm_proxy = &children[7]',
                'composite_child_init(pm_proxy',
                '"/vendor/bin/pm-proxy"',
                "COMPOSITE_ID_PER_PROXY",
            )
        ),
        "pm_proxy_order_is_bounded": all(
            token in matrix_fn
            for token in (
                f'streq(service_manager_order, "{pm_proxy_order}")',
                "property-shim,per_mgr_light,pm_proxy,mdm_helper,esoc0-fd-gate",
                "cnss_before_esoc.pm_proxy_start_attempted=1",
                "cnss_before_esoc_after_pm_proxy_start",
                "cnss_before_esoc.pm_proxy_started=%d",
                "cnss_before_esoc.pm_proxy.postflight_safe=%d",
            )
        ),
        "pm_proxy_before_mdm_helper": token_before(
            matrix_fn,
            "cnss_before_esoc.pm_proxy_start_attempted=1",
            "cnss_before_esoc.mdm_helper_start_attempted=1",
        ),
        "service_manager_after_mdm_gate_reused": all(
            token in matrix_fn
            for token in (
                "after_mdm_service_manager_order",
                "mdm_esoc_fd_seen &&",
                "start_cnss_before_esoc_service_manager_trio",
            )
        ),
        "pm_proxy_helper_blocked": "COMPOSITE_ID_PER_PROXY_HELPER" not in matrix_fn
        and '"/vendor/bin/pm_proxy_helper"' not in matrix_fn
        and "cnss_before_esoc.pm_proxy_helper_start_executed=0" in matrix_fn,
        "subsys_trigger_still_gated": all(
            token in matrix_fn
            for token in (
                "cnss_before_esoc.subsys_esoc0_controller_open_attempted=0",
                "cnss_before_esoc.subsys_esoc0_open_gate=cnss-wlfw-precondition",
                "cnss_before_esoc.wlfw_precondition_observed=%d",
            )
        ),
        "wifi_guardrails_preserved": all(
            token in matrix_fn
            for token in (
                "wifi_hal_start_executed=0",
                "scan_connect_linkup=0",
                "credentials=0",
                "dhcp_routing=0",
                "external_ping=0",
                "notify_attempted=0",
                "boot_done_attempted=0",
            )
        ),
        "cleanup_covers_pm_proxy": all(
            token in matrix_fn
            for token in (
                "composite_capture_observable_children(children, 8",
                "composite_cleanup_children(children, 8",
                "(!pm_proxy_matrix || cnss_before_esoc_child_postflight_safe(pm_proxy))",
            )
        ),
        "artifact_exists": repo_path(artifact).exists(),
        "build_passed": build_rc == 0,
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
        "strings_confirm_marker": "a90_android_execns_probe v159" in strings_output,
        "strings_confirm_pm_proxy_order": pm_proxy_order in strings_output,
        "strings_confirm_pm_proxy_phase": "cnss_before_esoc_after_pm_proxy_start" in strings_output,
    }
    passed = all(checks.values())
    return {
        "decision": "v955-pm-proxy-matrix-support-pass"
        if passed
        else "v955-pm-proxy-matrix-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v159 adds a bounded pm-proxy matrix order without pm_proxy_helper, subsystem open, HAL, scan/connect, DHCP, or external ping expansion"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v159 only, then run the bounded pm-proxy matrix comparator as a separate live gate"
            if passed
            else "repair helper v159 pm-proxy matrix support before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [(name, "PASS" if ok else "FAIL") for name, ok in manifest["checks"].items()]
    return "\n".join(
        [
            "# V955 PM-Proxy Matrix Support",
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
            "- no actor, daemon, service-manager, CNSS, or Wi-Fi HAL start",
            "- no `pm_proxy_helper`, eSoC ioctl, subsystem open, scan/connect, credentials, DHCP/routes, or external ping",
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
    wrapper = read_text(args.live_wrapper)
    classification = classify(source, wrapper, build_rc, build_log, args.build_artifact)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "helper_source": str(repo_path(args.helper_source)),
        "live_wrapper": str(repo_path(args.live_wrapper)),
        "build_artifact": str(repo_path(args.build_artifact)),
        "build_artifact_sha256": sha256(args.build_artifact),
        "build_log": str(repo_path(args.build_log)),
        "build_rc": build_rc,
        "device_commands_executed": False,
        "device_mutations": False,
        "actor_start_executed": False,
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
