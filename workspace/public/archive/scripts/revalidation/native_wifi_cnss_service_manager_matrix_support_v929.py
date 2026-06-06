#!/usr/bin/env python3
"""V929 source/build verifier for current CNSS/service-manager matrix support."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v929-cnss-service-manager-matrix-support")
LATEST_POINTER = Path("tmp/wifi/latest-v929-cnss-service-manager-matrix-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v929-execns-helper-v154-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v929-execns-helper-v154-build/build.log")
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


def ordered(text: str, *tokens: str) -> bool:
    offset = -1
    for token in tokens:
        found = text.find(token, offset + 1)
        if found < 0:
            return False
        offset = found
    return True


def artifact_strings(artifact: Path) -> str:
    if not repo_path(artifact).exists():
        return ""
    rc, output = run_host(["strings", str(artifact)], timeout=20)
    return output if rc == 0 else ""


def classify(source: str, build_rc: int, build_log: str, artifact: Path) -> dict[str, Any]:
    strings_output = artifact_strings(artifact)
    checks = {
        "execns_version_v154": 'EXECNS_VERSION "a90_android_execns_probe v154"' in source,
        "mode_exposed": "wifi-companion-mdm-helper-cnss-service-manager-matrix" in source,
        "allow_flag_exposed": "--allow-mdm-helper-cnss-service-manager-matrix" in source
        and "allow_mdm_helper_cnss_service_manager_matrix = true" in source,
        "order_enum_exposed": "--service-manager-order none|before-cnss|after-cnss|after-mdm-helper-esoc-fd"
        in source,
        "order_validation": all(
            token in source
            for token in (
                "is_cnss_service_manager_matrix_order",
                'streq(order, "none")',
                'streq(order, "before-cnss")',
                'streq(order, "after-cnss")',
                'streq(order, "after-mdm-helper-esoc-fd")',
            )
        ),
        "runtime_namespace_defaults": ordered(
            source,
            "is_wifi_companion_mdm_helper_cnss_before_subsys_trigger_capture_mode(cfg->mode) ||",
            "is_wifi_companion_mdm_helper_cnss_service_manager_matrix_mode(cfg->mode)",
            'cfg->vndk_apex_alias_mode = "v30-to-system-ext-v30"',
            'cfg->linkerconfig_mode = "copy-real"',
            'cfg->android_selinux_context_mode = "service-defaults"',
        ),
        "private_runtime_surfaces_include_matrix": all(
            token in source
            for token in (
                "cfg->allow_mdm_helper_cnss_service_manager_matrix",
                "materialize_private_properties",
                "materialize_service_manager_binder_devices",
                "property_service_shim_needed",
            )
        ),
        "service_manager_trio_spawn": all(
            token in source
            for token in (
                "start_cnss_before_esoc_service_manager_trio",
                '"/system/bin/servicemanager"',
                '"/system/bin/hwservicemanager"',
                '"/vendor/bin/vndservicemanager"',
                "apply_service_manager_identity_contract",
            )
        ),
        "matrix_order_branches": all(
            token in source
            for token in (
                'streq(service_manager_order, "before-cnss")',
                'streq(service_manager_order, "after-mdm-helper-esoc-fd")',
                'streq(service_manager_order, "after-cnss")',
                "cnss_before_esoc.service_manager_start_phase=%s",
            )
        ),
        "observability_keys": all(
            token in source
            for token in (
                "cnss_before_esoc.matrix_mode=%d",
                "cnss_before_esoc.service_manager_order=%s",
                "cnss_before_esoc.service_manager_start_requested=%d",
                "cnss_before_esoc.service_manager_started=%d",
                "cnss_before_esoc.servicemanager.postflight_safe=%d",
                "cnss_before_esoc.hwservicemanager.postflight_safe=%d",
                "cnss_before_esoc.vndservicemanager.postflight_safe=%d",
            )
        ),
        "guardrails_preserved": all(
            token in source
            for token in (
                "cnss_before_esoc.wifi_hal_start_executed=0",
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
        "strings_confirm_marker": "a90_android_execns_probe v154" in strings_output,
        "strings_confirm_new_mode": "wifi-companion-mdm-helper-cnss-service-manager-matrix"
        in strings_output,
        "strings_confirm_allow_flag": "--allow-mdm-helper-cnss-service-manager-matrix"
        in strings_output,
        "strings_confirm_order_enum": "--service-manager-order none|before-cnss|after-cnss|after-mdm-helper-esoc-fd"
        in strings_output,
        "strings_confirm_existing_compact_mode": "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"
        in strings_output
        and "--cnss-surface-mode full|compact" in strings_output,
    }
    passed = all(checks.values())
    return {
        "decision": "v929-cnss-service-manager-matrix-support-pass"
        if passed
        else "v929-cnss-service-manager-matrix-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v154 exposes a current CNSS/service-manager matrix mode with static build and no live action"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v154 only, then run one bounded matrix order at a time"
            if passed
            else "repair helper v154 source/build support before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [(name, "PASS" if ok else "FAIL") for name, ok in manifest["checks"].items()]
    return "\n".join(
        [
            "# V929 CNSS Service-Manager Matrix Support",
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
    manifest = {
        "generated_at": now_iso(),
        "tool": Path(__file__).name,
        "out_dir": str(args.out_dir),
        "helper_source": str(args.helper_source),
        "build_artifact": str(args.build_artifact),
        "build_log": str(args.build_log),
        "build_rc": build_rc,
        "build_artifact_sha256": sha256(args.build_artifact),
        "host": collect_host_metadata(),
        **classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
