#!/usr/bin/env python3
"""V1014 source/build verifier for after-fd Wi-Fi surface matrix support."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1014-after-fd-wifi-surface-matrix-support")
LATEST_POINTER = Path("tmp/wifi/latest-v1014-after-fd-wifi-surface-matrix-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v1014-execns-helper-v172-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v1014-execns-helper-v172-build/build.log")
BUILD_SCRIPT = Path("scripts/revalidation/build_android_execns_probe_helper.sh")

NEW_ORDER = "after-mdm-helper-esoc-fd-with-wifi-surface"


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


def ordered(text: str, *tokens: str) -> bool:
    offset = -1
    for token in tokens:
        found = text.find(token, offset + 1)
        if found < 0:
            return False
        offset = found
    return True


def classify(source: str, build_rc: int, build_log: str, artifact: Path) -> dict[str, Any]:
    matrix_fn = extract_static_function(
        source,
        "int",
        "run_wifi_companion_mdm_helper_cnss_before_subsys_trigger_capture_guarded",
    )
    strings_output = artifact_strings(artifact)
    checks = {
        "execns_version_v172": 'EXECNS_VERSION "a90_android_execns_probe v172"' in source,
        "order_usage_exposed": NEW_ORDER in source and f"--service-manager-order none|before-cnss|after-cnss|after-mdm-helper-esoc-fd|after-mdm-helper-esoc-fd-with-pm-proxy|{NEW_ORDER}" in source,
        "order_validator_accepts_wifi_surface": f'streq(order, "{NEW_ORDER}")' in source,
        "matrix_child_count_expanded": all(
            token in matrix_fn
            for token in (
                "struct composite_child children[11]",
                "struct composite_child *wifi_hal_legacy = &children[8]",
                "struct composite_child *wifi_hal_ext = &children[9]",
                "struct composite_child *wificond = &children[10]",
                "const size_t child_count = wifi_surface_matrix ? 11U : 8U",
            )
        ),
        "upper_actor_contracts_reused": all(
            token in matrix_fn
            for token in (
                '"/vendor/bin/hw/android.hardware.wifi@1.0-service"',
                '"/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service"',
                '"/system/bin/wificond"',
                "COMPOSITE_ID_WIFI_HAL",
                "COMPOSITE_ID_WIFICOND",
            )
        ),
        "after_fd_order_exposed": f'streq(service_manager_order, "{NEW_ORDER}")' in matrix_fn
        and "property-shim,per_mgr_light,mdm_helper,esoc0-fd-gate,servicemanager,hwservicemanager,vndservicemanager,wifi_hal_legacy,wifi_hal_ext,wificond,cnss_diag,cnss_daemon,wlfw-precondition-gate,subsys_esoc0-open-child" in matrix_fn,
        "wifi_surface_after_service_manager_before_cnss": ordered(
            matrix_fn,
            "start_cnss_before_esoc_service_manager_trio",
            "cnss_before_esoc.wifi_hal_start_attempted=1",
            "cnss_before_esoc.wificond_start_attempted=1",
            "cnss_before_esoc.cnss_diag_start_attempted=1",
        ),
        "cnss_gated_on_upper_surface": "(!wifi_surface_matrix || (wifi_hal_started && wificond_started))" in matrix_fn,
        "cleanup_covers_expanded_children": all(
            token in matrix_fn
            for token in (
                "composite_capture_observable_children(children, child_count",
                "composite_cleanup_children(children, child_count",
                "cnss_before_esoc.wifi_hal_legacy.postflight_safe=%d",
                "cnss_before_esoc.wifi_hal_ext.postflight_safe=%d",
                "cnss_before_esoc.wificond.postflight_safe=%d",
            )
        ),
        "no_scan_connect_expansion": all(
            token in matrix_fn
            for token in (
                "cnss_before_esoc.iwifi_start=0",
                "cnss_before_esoc.qcwlanstate_write=0",
                "cnss_before_esoc.scan_connect_linkup=0",
                "cnss_before_esoc.credentials=0",
                "cnss_before_esoc.dhcp_routing=0",
                "cnss_before_esoc.external_ping=0",
            )
        ),
        "no_esoc_controller_expansion": all(
            token in matrix_fn
            for token in (
                "cnss_before_esoc.subsys_esoc0_controller_open_attempted=0",
                "cnss_before_esoc.reg_req_eng_attempted=0",
                "cnss_before_esoc.notify_attempted=0",
                "cnss_before_esoc.boot_done_attempted=0",
            )
        ),
        "artifact_exists": repo_path(artifact).exists(),
        "build_passed": build_rc == 0,
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
        "strings_confirm_marker": "a90_android_execns_probe v172" in strings_output,
        "strings_confirm_new_order": NEW_ORDER in strings_output,
        "strings_confirm_wifi_surface_markers": all(
            token in strings_output
            for token in (
                "cnss_before_esoc.wifi_hal_legacy_start_attempted=1",
                "cnss_before_esoc.wifi_hal_ext_start_attempted=1",
                "cnss_before_esoc.wificond_start_attempted=1",
                "cnss_before_esoc.iwifi_start=0",
                "cnss_before_esoc.qcwlanstate_write=0",
            )
        ),
    }
    passed = all(checks.values())
    return {
        "decision": "v1014-after-fd-wifi-surface-matrix-support-pass"
        if passed
        else "v1014-after-fd-wifi-surface-matrix-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v172 adds a source/build-only after-fd Wi-Fi surface matrix that preserves the mdm_helper fd gate and adds dual HAL/wificond before CNSS without scan/connect"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v172 only, then run a separate bounded after-fd Wi-Fi surface matrix live gate"
            if passed
            else "repair helper v172 source/build support before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [(name, "PASS" if ok else "FAIL") for name, ok in manifest["checks"].items()]
    return "\n".join(
        [
            "# V1014 After-Fd Wi-Fi Surface Matrix Support",
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
            "- no device command, deploy, actor start, daemon start, or service-manager start",
            "- new runtime order still forbids `IWifi.start`, `qcwlanstate`, scan/connect, credentials, DHCP/routes, external ping, eSoC controller ioctls, notify, and BOOT_DONE",
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
        "tool": Path(__file__).name,
        "out_dir": str(args.out_dir),
        "helper_source": str(args.helper_source),
        "build_artifact": str(args.build_artifact),
        "build_log": str(args.build_log),
        "build_rc": build_rc,
        "build_artifact_sha256": sha256(args.build_artifact),
        "host": collect_host_metadata(),
        "host_only": True,
        "device_commands_executed": False,
        "deploy_executed": False,
        "native_live_executed": False,
        **classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
