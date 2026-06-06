#!/usr/bin/env python3
"""V983 source/build verifier for Android service-window property service shim coverage."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v983-android-service-window-property-shim")
LATEST_POINTER = Path("tmp/wifi/latest-v983-android-service-window-property-shim.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v983-execns-helper-v166-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v983-execns-helper-v166-build/build.log")
BUILD_SCRIPT = Path("scripts/revalidation/build_android_execns_probe_helper.sh")
MODE = "wifi-companion-android-wifi-service-window-start-only"


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


def function_body(source: str, return_type: str, name: str) -> str:
    match = re.search(rf"\nstatic {re.escape(return_type)} {re.escape(name)}\([^)]*\) \{{", source)
    if not match:
        return ""
    start = match.start() + 1
    next_match = re.search(r"\nstatic\s+", source[start + 1 :])
    return source[start:] if not next_match else source[start : start + 1 + next_match.start()]


def classify(source: str, build_rc: int, build_log: str, artifact: Path) -> dict[str, Any]:
    shim_fn = function_body(source, "bool", "property_service_shim_needed")
    materialize_fn = function_body(source, "int", "materialize_service_manager_binder_devices")
    strings_output = artifact_strings(artifact)
    checks = {
        "execns_version_v166": 'EXECNS_VERSION "a90_android_execns_probe v166"' in source,
        "property_shim_has_android_service_window_condition": (
            "is_wifi_companion_android_wifi_service_window_start_only_mode(cfg->mode)" in shim_fn
            and "return cfg->allow_android_wifi_service_window;" in shim_fn
        ),
        "binder_materialization_still_has_android_service_window_condition": (
            "is_wifi_companion_android_wifi_service_window_start_only_mode(cfg->mode)" in materialize_fn
            and "cfg->allow_android_wifi_service_window" in materialize_fn
        ),
        "property_shim_start_path_still_used": "start_property_service_shim(cfg, paths, &property_shim, stdout_buf)" in source,
        "dedicated_mode_still_uses_single_allow_flag": "accepts only --allow-android-wifi-service-window" in source,
        "guardrails_still_present": all(
            token in source
            for token in (
                "android_wifi_service_window.qcwlanstate_write=0",
                "android_wifi_service_window.iwifi_start=0",
                "android_wifi_service_window.subsys_esoc0_open_attempted=0",
                "android_wifi_service_window.esoc_ioctl_attempted=0",
                "android_wifi_service_window.scan_connect_linkup=0",
                "android_wifi_service_window.credentials=0",
                "android_wifi_service_window.dhcp_routing=0",
                "android_wifi_service_window.external_ping=0",
            )
        ),
        "artifact_exists": repo_path(artifact).exists(),
        "build_passed": build_rc == 0,
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
        "strings_confirm_version": "a90_android_execns_probe v166" in strings_output,
        "strings_confirm_mode": MODE in strings_output,
    }
    passed = all(checks.values())
    return {
        "decision": "v983-android-service-window-property-shim-pass"
        if passed
        else "v983-android-service-window-property-shim-incomplete",
        "pass": passed,
        "reason": (
            "helper v166 enables the private property service shim for the dedicated Android service-window mode"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v166, then rerun the bounded Android service-window live proof"
            if passed
            else "repair property shim coverage before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [(name, "PASS" if ok else "FAIL") for name, ok in manifest["checks"].items()]
    return "\n".join(
        [
            "# V983 Android Service-Window Property Shim",
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
