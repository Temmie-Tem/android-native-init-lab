#!/usr/bin/env python3
"""V961 source/build verifier for explicit post-provider subsystem trigger gating."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v961-post-provider-trigger-gate-support")
LATEST_POINTER = Path("tmp/wifi/latest-v961-post-provider-trigger-gate-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v961-execns-helper-v160-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v961-execns-helper-v160-build/build.log")
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


def token_before(text: str, first: str, second: str) -> bool:
    first_index = text.find(first)
    second_index = text.find(second)
    return first_index >= 0 and second_index >= 0 and first_index < second_index


def classify(source: str, build_rc: int, build_log: str, artifact: Path) -> dict[str, Any]:
    matrix_fn = extract_static_function(
        source,
        "int",
        "run_wifi_companion_mdm_helper_cnss_before_subsys_trigger_capture_guarded",
    )
    trigger_fn = extract_static_function(
        source,
        "int",
        "start_cnss_before_esoc_subsys_trigger_child",
    )
    strings_output = artifact_strings(artifact)
    post_gate = "post-provider-no-wlfw"
    pm_proxy_order = "after-mdm-helper-esoc-fd-with-pm-proxy"
    checks = {
        "execns_version_v160": 'EXECNS_VERSION "a90_android_execns_probe v160"' in source,
        "gate_option_exposed": "--subsys-trigger-gate wlfw-precondition|post-provider-no-wlfw" in source,
        "gate_config_default_preserves_existing_behavior": all(
            token in source
            for token in (
                'const char *subsys_trigger_gate;',
                'cfg->subsys_trigger_gate = "wlfw-precondition";',
                "cfg->subsys_trigger_gate_explicit = true;",
            )
        ),
        "gate_validator_accepts_only_two_values": all(
            token in source
            for token in (
                "static bool is_cnss_subsys_trigger_gate",
                'streq(gate, "wlfw-precondition")',
                f'streq(gate, "{post_gate}")',
                "invalid --subsys-trigger-gate",
            )
        ),
        "post_provider_gate_restricted_to_pm_proxy_matrix": all(
            token in source
            for token in (
                f'streq(cfg->subsys_trigger_gate, "{post_gate}")',
                "is_wifi_companion_mdm_helper_cnss_service_manager_matrix_mode(cfg->mode)",
                f'streq(cfg->service_manager_order, "{pm_proxy_order}")',
            )
        ),
        "trigger_child_records_selected_gate": all(
            token in trigger_fn
            for token in (
                "cnss_before_esoc.subsys_trigger.gate=%s",
                "cnss_before_esoc.subsys_esoc0_open_gate=%s",
                "cfg->subsys_trigger_gate",
            )
        ),
        "trigger_child_guardrails_preserved": all(
            token in trigger_fn
            for token in (
                "O_RDONLY | O_NONBLOCK | O_CLOEXEC",
                "cnss_before_esoc.subsys_trigger.no_notify=1",
                "cnss_before_esoc.subsys_trigger.no_boot_done=1",
            )
        ),
        "post_provider_gate_arms_after_full_provider_stack": all(
            token in matrix_fn
            for token in (
                "post_provider_trigger_ready",
                "surface_poll_count > 0",
                "mdm_esoc_fd_seen",
                "pm_proxy_started",
                "service_manager_started",
                "cnss_diag_started",
                "cnss_daemon_started",
            )
        ),
        "post_provider_gate_requires_wlfw_absent": all(
            token in matrix_fn
            for token in (
                "!wlfw_precondition_observed",
                "cnss_before_esoc.post_provider_no_wlfw_gate_ready=%d",
                "post_provider_no_wlfw_trigger_started",
            )
        ),
        "post_provider_gate_starts_after_surface_poll": token_before(
            matrix_fn,
            "cnss_before_esoc.wlfw_precondition_poll=%d",
            "start_cnss_before_esoc_subsys_trigger_child",
        ),
        "result_taxonomy_separates_new_gate": all(
            token in matrix_fn
            for token in (
                "post-provider-no-wlfw-trigger-clean",
                "post-provider-no-wlfw-gate-opened-subsys-esoc0-child-finished-or-was-cleaned",
                "wlfw-precondition-missing-no-open",
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
                "pm_proxy_helper_start_executed=0",
            )
        ),
        "artifact_exists": repo_path(artifact).exists(),
        "build_passed": build_rc == 0,
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
        "strings_confirm_version": "a90_android_execns_probe v160" in strings_output,
        "strings_confirm_gate": post_gate in strings_output,
        "strings_confirm_result": "post-provider-no-wlfw-trigger-clean" in strings_output,
    }
    passed = all(checks.values())
    return {
        "decision": "v961-post-provider-trigger-gate-support-pass"
        if passed
        else "v961-post-provider-trigger-gate-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v160 adds an explicit post-provider-no-wlfw subsystem trigger gate while preserving the default WLFW-precondition gate"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v160 only, then run a bounded live post-provider trigger proof as a separate gate"
            if passed
            else "repair helper v160 post-provider trigger gate support before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [(name, "PASS" if ok else "FAIL") for name, ok in manifest["checks"].items()]
    return "\n".join(
        [
            "# V961 Post-Provider Trigger Gate Support",
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
            "- default gate remains `wlfw-precondition`",
            "- new gate is valid only with the `pm-proxy` matrix order",
            "- no device command",
            "- no actor, daemon, service-manager, CNSS, or Wi-Fi HAL start by the verifier",
            "- no `pm_proxy_helper`, eSoC notify, boot-done, scan/connect, credentials, DHCP/routes, or external ping",
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
