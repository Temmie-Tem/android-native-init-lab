#!/usr/bin/env python3
"""V967 source/build verifier for Android Wi-Fi service-window start-only support."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v967-android-wifi-service-window-support")
LATEST_POINTER = Path("tmp/wifi/latest-v967-android-wifi-service-window-support.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_BUILD_ARTIFACT = Path("tmp/wifi/v967-execns-helper-v161-build/a90_android_execns_probe")
DEFAULT_BUILD_LOG = Path("tmp/wifi/v967-execns-helper-v161-build/build.log")
BUILD_SCRIPT = Path("scripts/revalidation/build_android_execns_probe_helper.sh")

MODE = "wifi-companion-android-wifi-service-window-start-only"
ALLOW_FLAG = "--allow-android-wifi-service-window"
ORDER = (
    "servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,rmt_storage,"
    "tftp_server,pd_mapper,wifi_hal_legacy,wifi_hal_ext,per_mgr,cnss_diag,"
    "wificond,mdm_helper,cnss_daemon"
)
EXPECTED_CHILDREN = [
    ("servicemanager", "/system/bin/servicemanager"),
    ("hwservicemanager", "/system/bin/hwservicemanager"),
    ("vndservicemanager", "/vendor/bin/vndservicemanager"),
    ("qrtr_ns", "/vendor/bin/qrtr-ns"),
    ("rmt_storage", "/vendor/bin/rmt_storage"),
    ("tftp_server", "/vendor/bin/tftp_server"),
    ("pd_mapper", "/vendor/bin/pd-mapper"),
    ("wifi_hal_legacy", "/vendor/bin/hw/android.hardware.wifi@1.0-service"),
    ("wifi_hal_ext", "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service"),
    ("per_mgr", "/vendor/bin/pm-service"),
    ("cnss_diag", "/vendor/bin/cnss_diag"),
    ("wificond", "/system/bin/wificond"),
    ("mdm_helper", "/vendor/bin/mdm_helper"),
    ("cnss_daemon", "/vendor/bin/cnss-daemon"),
]


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


def ordered_tokens(text: str, tokens: list[str]) -> bool:
    offset = 0
    for token in tokens:
        index = text.find(token, offset)
        if index < 0:
            return False
        offset = index + len(token)
    return True


def classify(source: str, build_rc: int, build_log: str, artifact: Path) -> dict[str, Any]:
    service_fn = extract_static_function(
        source,
        "int",
        "run_wifi_companion_android_wifi_service_window_guarded",
    )
    dispatch_start = source.find("is_wifi_companion_mdm_helper_cnss_service_manager_matrix_mode(cfg.mode)")
    dispatch_end = source.find('streq(cfg.mode, "private-selinux-proof")', dispatch_start)
    dispatch_block = source[dispatch_start:dispatch_end] if dispatch_start >= 0 and dispatch_end > dispatch_start else ""
    strings_output = artifact_strings(artifact)
    child_name_tokens = [f'"{name}"' for name, _path in EXPECTED_CHILDREN]
    child_path_tokens = [f'"{path}"' for _name, path in EXPECTED_CHILDREN]
    safety_tokens = (
        "android_wifi_service_window.qcwlanstate_write=0",
        "android_wifi_service_window.iwifi_start=0",
        "android_wifi_service_window.subsys_esoc0_open_attempted=0",
        "android_wifi_service_window.esoc_ioctl_attempted=0",
        "android_wifi_service_window.scan_connect_linkup=0",
        "android_wifi_service_window.credentials=0",
        "android_wifi_service_window.dhcp_routing=0",
        "android_wifi_service_window.external_ping=0",
    )
    checks = {
        "execns_version_v161": 'EXECNS_VERSION "a90_android_execns_probe v161"' in source,
        "mode_and_allow_flag_exposed": MODE in source and ALLOW_FLAG in source,
        "predicate_added": (
            "is_wifi_companion_android_wifi_service_window_start_only_mode" in source
            and f'streq(mode, "{MODE}")' in source
        ),
        "parser_sets_allow_flag": (
            f'strcmp(argv[i], "{ALLOW_FLAG}") == 0' in source
            and "cfg->allow_android_wifi_service_window = true;" in source
        ),
        "default_namespace_matches_android_window": all(
            token in source
            for token in (
                'cfg->data_wifi_mode = "private-empty";',
                'cfg->null_device_mode = "dev-null";',
                'cfg->vndk_apex_alias_mode = "v30-to-system-ext-v30";',
                'cfg->linkerconfig_mode = "copy-real";',
                'cfg->linkerconfig_source = "/cache/bin/a90_real_ld.config.txt";',
                'cfg->apex_libraries_source = "/cache/bin/a90_real_apex.libraries.config.txt";',
                'cfg->android_selinux_context_mode = "service-defaults";',
                'cfg->cnss_surface_mode = "full";',
            )
        ),
        "mode_allowed_by_v235_allowlist": (
            "arguments do not match v235 allowlist" in source
            and "is_wifi_companion_android_wifi_service_window_start_only_mode(cfg->mode)" in source
        ),
        "allow_flag_restricted_to_mode": (
            "--allow-android-wifi-service-window is only valid with "
            "wifi-companion-android-wifi-service-window-start-only mode"
        )
        in source,
        "mode_rejects_unrelated_proof_flags": all(
            token in source
            for token in (
                "wifi-companion-android-wifi-service-window-start-only accepts only",
                "cfg->allow_iwifi_start_only",
                "cfg->allow_scan_only",
                "cfg->allow_connect_dhcp_ping",
                "cfg->allow_esoc_req_registered_subsys_hold_preflight",
                "cfg->allow_mdm_helper_cnss_service_manager_matrix",
            )
        ),
        "service_window_function_present": bool(service_fn),
        "service_window_order_recorded": f"android_wifi_service_window.order={ORDER}" in service_fn,
        "service_window_child_names_ordered": ordered_tokens(service_fn, child_name_tokens),
        "service_window_child_paths_ordered": ordered_tokens(service_fn, child_path_tokens),
        "service_window_uses_full_surface_capture": all(
            token in service_fn
            for token in (
                "append_qipcrtr_protocol_summary",
                "append_wifi_window_surface_capture",
                "append_wifi_cnss2_focus_capture",
                "append_wifi_runtime_surface_snapshot",
                "cnss_before_esoc_wlfw_precondition_observed",
            )
        ),
        "blocked_path_is_no_exec": all(
            token in service_fn
            for token in (
                "android_wifi_service_window.allowed=0",
                "android_wifi_service_window.exec_attempted=0",
                "android_wifi_service_window.service_manager_start_executed=0",
                "android_wifi_service_window.wifi_hal_start_executed=0",
                "android_wifi_service_window.wificond_start_executed=0",
                "android_wifi_service_window.mdm_helper_start_executed=0",
                "android_wifi_service_window.cnss_daemon_start_executed=0",
                "android_wifi_service_window.child_started=0",
                "android_wifi_service_window.result=start-only-blocked",
            )
        ),
        "allowed_path_marks_actual_starts": all(
            token in service_fn
            for token in (
                "android_wifi_service_window.allowed=1",
                "android_wifi_service_window.exec_attempted=1",
                "android_wifi_service_window.service_manager_start_executed=1",
                "android_wifi_service_window.wifi_hal_start_executed=1",
                "android_wifi_service_window.wificond_start_executed=1",
                "android_wifi_service_window.mdm_helper_start_executed=1",
                "android_wifi_service_window.cnss_daemon_start_executed=1",
            )
        ),
        "hard_guardrail_markers_present": all(token in service_fn for token in safety_tokens),
        "result_taxonomy_present": all(
            token in service_fn
            for token in (
                "wlfw-precondition-observed",
                "service-window-no-wlfw",
                "start-only-runtime-gap",
                "start-only-reboot-required",
                "manual-review-required",
            )
        ),
        "main_dispatches_before_generic_modes": ordered_tokens(
            dispatch_block,
            [
                "is_wifi_companion_android_wifi_service_window_start_only_mode",
                "run_wifi_companion_android_wifi_service_window_guarded",
                "is_wifi_companion_any_start_only_mode",
            ],
        ),
        "artifact_exists": repo_path(artifact).exists(),
        "build_passed": build_rc == 0,
        "artifact_static": "statically linked" in build_log and "There is no dynamic section" in build_log,
        "strings_confirm_version": "a90_android_execns_probe v161" in strings_output,
        "strings_confirm_mode": MODE in strings_output,
        "strings_confirm_guardrails": all(token in strings_output for token in safety_tokens),
        "strings_confirm_results": all(
            token in strings_output
            for token in ("wlfw-precondition-observed", "service-window-no-wlfw", "start-only-blocked")
        ),
    }
    passed = all(checks.values())
    return {
        "decision": "v967-android-wifi-service-window-support-pass"
        if passed
        else "v967-android-wifi-service-window-support-incomplete",
        "pass": passed,
        "reason": (
            "helper v161 adds guarded Android Wi-Fi service-window start-only support with no qcwlanstate, eSoC, scan/connect, DHCP, credential, or external ping path"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "deploy helper v161 only, then run a bounded live Android service-window proof as a separate gate; Android dmesg GPIO/esoc timing can be a parallel host-only classifier"
            if passed
            else "repair helper v161 Android Wi-Fi service-window support before deploy"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [(name, "PASS" if ok else "FAIL") for name, ok in manifest["checks"].items()]
    return "\n".join(
        [
            "# V967 Android Wi-Fi Service Window Support",
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
            "- no service-window actor start by the verifier",
            "- no `qcwlanstate` write",
            "- no `/dev/subsys_esoc0` open or eSoC ioctl path",
            "- no `IWifi.start`, scan/connect/link-up, credentials, DHCP/routes, or external ping",
            "- live deploy/run remains a separate bounded gate",
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
        "qcwlanstate_write_executed": False,
        "esoc_open_executed": False,
        "esoc_ioctl_executed": False,
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
